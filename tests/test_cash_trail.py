from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.cash_trail import import_cash_trail
from src import cli
from src.db import TrackerDB
from src.export_web import build_dashboard_payload

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def test_synthetic_import_is_separate_idempotent_and_cash_range_is_visible(tmp_path: Path):
    db = TrackerDB(tmp_path / "tracker.db")
    invoice = FIXTURES / "cash_trail_invoice_sample.csv"
    bank = FIXTURES / "cash_trail_bank_sample.csv"
    links = FIXTURES / "cash_trail_links_sample.csv"

    import_cash_trail(db, invoice_csv=invoice, bank_csv=bank, links_csv=links)
    import_cash_trail(db, invoice_csv=invoice, bank_csv=bank, links_csv=links)

    rows = db.fetch_all_events()
    assert len(rows) == 4
    assert all(row["money_rail"] == "invoice_line" for row in rows)
    assert all(
        row[column] is None
        for row in rows
        for column in (
            "input_tokens",
            "output_tokens",
            "cached_input_tokens",
            "reasoning_tokens",
            "cache_write_input_tokens",
            "total_tokens",
        )
    )
    assert all(row["currency"] == "USD" for row in rows)
    assert len(db.fetch_cash_links()) == 1
    assert db.conn.execute("SELECT COUNT(*) FROM cash_link_history").fetchone()[0] == 1

    payload = build_dashboard_payload(db)
    cash = payload["cash_trail"]
    assert cash["links"][0]["status"] == "confirmed"
    assert cash["ranges"] == [
        {
            "currency": "USD",
            "lower": 26.6,
            "upper": 58.01,
            "pending": 0.0,
            "unresolved_invoices": 1,
            "partial_remainders": 0,
        }
    ]
    assert payload["totals"]["cost_usd_priced"] == 58.01
    assert payload["totals"]["cost_by_rail"]["invoice_line"] == 58.01
    assert sum(row["cash_supporting_only"] for row in payload["events"]) == 1
    db.close()


def test_fuzzy_match_stays_candidate_and_status_history_is_auditable(tmp_path: Path):
    invoice = _write_csv(
        tmp_path / "invoice.csv",
        ["source_record_id", "source_product", "invoice_date", "amount_usd", "currency", "merchant"],
        [["inv_fake_1", "synthetic_ai", "2026-09-01", "12.00", "USD", "Example AI Labs"]],
    )
    bank = _write_csv(
        tmp_path / "bank.csv",
        ["source_record_id", "posted_date", "amount_usd", "currency", "direction", "descriptor", "status"],
        [["txn_fake_1", "2026-09-02", "12.00", "USD", "debit", "EXAMPLE AI LABS DEMO", "posted"]],
    )
    db = TrackerDB(tmp_path / "tracker.db")
    import_cash_trail(db, invoice_csv=invoice, bank_csv=bank)

    link = db.fetch_cash_links()[0]
    assert link["status"] == "candidate"
    assert link["confirmed_by"] is None
    db.upsert_cash_link({
        **link,
        "relation": "settles",
        "status": "confirmed",
        "confirmed_by": "operator",
    })
    assert [row[0] for row in db.conn.execute(
        "SELECT status FROM cash_link_history ORDER BY history_id"
    )] == ["candidate", "confirmed"]
    db.close()


def test_native_currency_pending_and_partial_settlement_are_explicit(
    tmp_path: Path, monkeypatch
):
    invoice = _write_csv(
        tmp_path / "invoice.csv",
        ["source_record_id", "source_product", "invoice_date", "amount_native", "currency", "merchant"],
        [["inv_fake_eur", "synthetic_ai", "2026-09-01", "100.00", "EUR", "Fictional Vendor"]],
    )
    bank = _write_csv(
        tmp_path / "bank.csv",
        ["source_record_id", "posted_date", "amount_native", "currency", "direction", "descriptor", "status"],
        [
            ["txn_pending", "2026-09-02", "3.00", "EUR", "debit", "DEMO PENDING", "pending"],
            ["txn_partial", "2026-09-03", "40.00", "EUR", "debit", "FICTIONAL VENDOR", "posted"],
        ],
    )
    links = _write_csv(
        tmp_path / "links.csv",
        ["invoice_source_record_id", "settlement_source_record_id", "relation", "status", "confirmed_by", "matched_on"],
        [["inv_fake_eur", "txn_partial", "partial_settlement", "confirmed", "operator", "amount,currency"]],
    )
    db = TrackerDB(tmp_path / "tracker.db")
    import_cash_trail(db, invoice_csv=invoice, bank_csv=bank, links_csv=links)

    events = db.fetch_all_events()
    assert all(row["cost_usd"] is None for row in events)
    assert all(row["currency"] == "EUR" for row in events)
    payload = build_dashboard_payload(db)["cash_trail"]
    assert payload["ranges"] == [
        {
            "currency": "EUR",
            "lower": 40.0,
            "upper": 100.0,
            "pending": 3.0,
            "unresolved_invoices": 0,
            "partial_remainders": 1,
        }
    ]
    assert payload["pending_count"] == 1
    session = next(
        row for row in build_dashboard_payload(db)["sessions"]
        if row["currency"] == "EUR" and row["amount_native"] == 40.0
    )
    assert session["amount_native"] == 40.0
    assert session["coverage"] == "1/1"
    monkeypatch.setattr(cli, "DB_PATH", tmp_path / "tracker.db")
    monkeypatch.setattr(cli, "PRICING", ROOT / "config" / "PRICING_MODELS.csv")
    assert cli.cmd_reprice(argparse.Namespace()) == 0
    assert next(
        row for row in db.fetch_all_events()
        if row["source_surface"] == "provider_invoice"
    )["evidence_class"] == "OBS"
    db.close()


def test_refund_is_signed_and_confirmed_pair_counts_once(tmp_path: Path):
    invoice = _write_csv(
        tmp_path / "invoice.csv",
        ["source_record_id", "source_product", "invoice_date", "amount_usd", "currency", "merchant", "status"],
        [["credit_demo", "synthetic_ai", "2026-09-01", "5.00", "USD", "Example AI Labs", "credit_note"]],
    )
    bank = _write_csv(
        tmp_path / "bank.csv",
        ["source_record_id", "posted_date", "amount_usd", "currency", "direction", "descriptor", "status"],
        [["refund_demo", "2026-09-02", "5.00", "USD", "credit", "EXAMPLE AI LABS", "posted"]],
    )
    links = _write_csv(
        tmp_path / "links.csv",
        ["invoice_source_record_id", "settlement_source_record_id", "relation", "status", "confirmed_by", "matched_on"],
        [["credit_demo", "refund_demo", "refunds", "confirmed", "operator", "amount,currency"]],
    )
    db = TrackerDB(tmp_path / "tracker.db")
    import_cash_trail(db, invoice_csv=invoice, bank_csv=bank, links_csv=links)

    events = db.fetch_all_events()
    bank_event = next(row for row in events if row["source_surface"] == "bank_statement")
    assert bank_event["amount_native"] == -5.0
    assert build_dashboard_payload(db)["cash_trail"]["ranges"] == [
        {
            "currency": "USD",
            "lower": -5.0,
            "upper": -5.0,
            "pending": 0.0,
            "unresolved_invoices": 0,
            "partial_remainders": 0,
        }
    ]
    db.close()


def test_invalid_link_does_not_partially_import_events(tmp_path: Path):
    invoice = _write_csv(
        tmp_path / "invoice.csv",
        ["source_record_id", "source_product", "invoice_date", "amount_usd", "currency"],
        [["inv_fake", "synthetic_ai", "2026-09-01", "5.00", "USD"]],
    )
    links = _write_csv(
        tmp_path / "links.csv",
        ["invoice_source_record_id", "settlement_source_record_id", "relation", "status", "confirmed_by", "matched_on"],
        [["inv_fake", "missing_bank", "settles", "confirmed", "operator", "manual"]],
    )
    db = TrackerDB(tmp_path / "tracker.db")
    try:
        import_cash_trail(db, invoice_csv=invoice, links_csv=links)
    except ValueError as exc:
        assert "unknown source_record_id" in str(exc)
    else:
        raise AssertionError("invalid link import should fail")
    assert db.count_events() == 0
    db.close()


def test_cross_currency_link_is_rejected_before_import(tmp_path: Path):
    invoice = _write_csv(
        tmp_path / "invoice.csv",
        ["source_record_id", "source_product", "invoice_date", "amount_native", "currency"],
        [["inv_eur", "synthetic_ai", "2026-09-01", "10.00", "EUR"]],
    )
    bank = _write_csv(
        tmp_path / "bank.csv",
        ["source_record_id", "posted_date", "amount_native", "currency", "direction", "status"],
        [["txn_usd", "2026-09-02", "3.00", "USD", "debit", "posted"]],
    )
    links = _write_csv(
        tmp_path / "links.csv",
        ["invoice_source_record_id", "settlement_source_record_id", "relation", "status", "confirmed_by", "matched_on"],
        [["inv_eur", "txn_usd", "partial_settlement", "confirmed", "operator", "manual"]],
    )
    db = TrackerDB(tmp_path / "tracker.db")
    try:
        import_cash_trail(db, invoice_csv=invoice, bank_csv=bank, links_csv=links)
    except ValueError as exc:
        assert "matching currencies" in str(exc)
    else:
        raise AssertionError("cross-currency cash link should fail")
    assert db.count_events() == 0
    assert db.fetch_cash_links() == []
    db.close()


def test_partial_settlements_sum_without_float_remainders(tmp_path: Path):
    invoice = _write_csv(
        tmp_path / "invoice.csv",
        ["source_record_id", "source_product", "invoice_date", "amount_usd", "currency", "merchant"],
        [["inv_shared", "synthetic_ai", "2026-09-01", "100.00", "USD", "Fictional Vendor"]],
    )
    bank = _write_csv(
        tmp_path / "bank.csv",
        ["source_record_id", "posted_date", "amount_usd", "currency", "direction", "descriptor", "status"],
        [
            ["txn_shared", "2026-09-02", "60.00", "USD", "debit", "Fictional Vendor", "posted"],
            ["txn_second", "2026-09-03", "40.00", "USD", "debit", "Fictional Vendor", "posted"],
        ],
    )
    links = _write_csv(
        tmp_path / "links.csv",
        ["invoice_source_record_id", "settlement_source_record_id", "relation", "status", "confirmed_by", "matched_on"],
        [
            ["inv_shared", "txn_shared", "partial_settlement", "confirmed", "operator", "manual"],
            ["inv_shared", "txn_second", "partial_settlement", "confirmed", "operator", "manual"],
        ],
    )
    db = TrackerDB(tmp_path / "tracker.db")
    import_cash_trail(db, invoice_csv=invoice, bank_csv=bank, links_csv=links)
    cash = build_dashboard_payload(db)["cash_trail"]
    assert cash["ranges"][0]["lower"] == cash["ranges"][0]["upper"] == 100.0
    assert cash["ranges"][0]["partial_remainders"] == 0
    db.close()


def test_one_bank_row_cannot_be_allocated_to_two_invoices(tmp_path: Path):
    invoice = _write_csv(
        tmp_path / "invoice.csv",
        ["source_record_id", "source_product", "invoice_date", "amount_usd", "currency"],
        [
            ["inv_share_a", "synthetic_ai", "2026-09-01", "120.00", "USD"],
            ["inv_share_b", "synthetic_ai", "2026-09-01", "120.00", "USD"],
        ],
    )
    bank = _write_csv(
        tmp_path / "bank.csv",
        ["source_record_id", "posted_date", "amount_usd", "currency", "direction", "status"],
        [["txn_share", "2026-09-02", "100.00", "USD", "debit", "posted"]],
    )
    links = _write_csv(
        tmp_path / "links.csv",
        ["invoice_source_record_id", "settlement_source_record_id", "relation", "status", "confirmed_by", "matched_on"],
        [
            ["inv_share_a", "txn_share", "partial_settlement", "confirmed", "operator", "manual"],
            ["inv_share_b", "txn_share", "partial_settlement", "confirmed", "operator", "manual"],
        ],
    )
    db = TrackerDB(tmp_path / "tracker.db")
    try:
        import_cash_trail(db, invoice_csv=invoice, bank_csv=bank, links_csv=links)
    except ValueError as exc:
        assert "only one confirmed settlement relationship" in str(exc)
    else:
        raise AssertionError("a posted row must not be allocated twice")
    assert db.count_events() == 0
    assert db.fetch_cash_links() == []
    db.close()


def test_correction_supersedes_old_revision_and_stale_reimport_does_not_revert(
    tmp_path: Path,
):
    db = TrackerDB(tmp_path / "tracker.db")
    old_invoice = _write_csv(
        tmp_path / "invoice-old.csv",
        ["source_record_id", "source_product", "invoice_date", "amount_usd", "currency", "merchant"],
        [["inv_revision", "synthetic_ai", "2026-09-01", "10.00", "USD", "Fictional Vendor"]],
    )
    bank = _write_csv(
        tmp_path / "bank.csv",
        ["source_record_id", "posted_date", "amount_usd", "currency", "direction", "descriptor", "status"],
        [["txn_revision", "2026-09-02", "10.00", "USD", "debit", "Fictional Vendor", "posted"]],
    )
    links = _write_csv(
        tmp_path / "links.csv",
        ["invoice_source_record_id", "settlement_source_record_id", "relation", "status", "confirmed_by", "matched_on"],
        [["inv_revision", "txn_revision", "settles", "confirmed", "operator", "manual"]],
    )
    import_cash_trail(db, invoice_csv=old_invoice, bank_csv=bank, links_csv=links)
    corrected = _write_csv(
        tmp_path / "invoice-corrected.csv",
        ["source_record_id", "source_product", "invoice_date", "amount_usd", "currency", "merchant"],
        [["inv_revision", "synthetic_ai", "2026-09-01", "12.00", "USD", "Fictional Vendor"]],
    )
    import_cash_trail(db, invoice_csv=corrected)
    import_cash_trail(db, invoice_csv=old_invoice)

    invoices = [
        row for row in db.fetch_all_events()
        if row["source_surface"] == "provider_invoice"
    ]
    assert len(invoices) == 2
    assert sum(row["cash_superseded_by"] is None for row in invoices) == 1
    active = next(row for row in invoices if row["cash_superseded_by"] is None)
    assert active["amount_native"] == 12.0
    payload = build_dashboard_payload(db)
    assert sum(not row["cash_current"] for row in payload["events"]) == 1
    assert payload["cash_trail"]["ranges"][0]["upper"] == 22.0
    db.close()


def test_missing_merchants_need_an_exact_amount_to_create_candidate(tmp_path: Path):
    invoice = _write_csv(
        tmp_path / "invoice.csv",
        ["source_record_id", "source_product", "invoice_date", "amount_usd", "currency"],
        [["inv_no_merchant", "synthetic_ai", "2026-09-01", "12.00", "USD"]],
    )
    bank = _write_csv(
        tmp_path / "bank.csv",
        ["source_record_id", "posted_date", "amount_usd", "currency", "direction", "status"],
        [["txn_no_merchant", "2026-09-02", "5.00", "USD", "debit", "posted"]],
    )
    db = TrackerDB(tmp_path / "tracker.db")
    import_cash_trail(db, invoice_csv=invoice, bank_csv=bank)
    assert db.fetch_cash_links() == []
    db.close()


def test_source_product_is_validated_as_an_identifier(tmp_path: Path):
    invoice = _write_csv(
        tmp_path / "invoice.csv",
        ["source_record_id", "source_product", "invoice_date", "amount_usd", "currency"],
        [["inv_html", '<img src=x onerror="alert(1)">', "2026-09-01", "12.00", "USD"]],
    )
    db = TrackerDB(tmp_path / "tracker.db")
    try:
        import_cash_trail(db, invoice_csv=invoice)
    except ValueError as exc:
        assert "safe identifier" in str(exc)
    else:
        raise AssertionError("HTML product identifier should fail validation")
    assert db.count_events() == 0
    db.close()


def test_fixture_files_are_synthetic_only():
    files = (
        "cash_trail_invoice_sample.csv",
        "cash_trail_bank_sample.csv",
        "cash_trail_links_sample.csv",
    )
    content = "\n".join((FIXTURES / name).read_text(encoding="utf-8") for name in files).lower()
    for forbidden in ("auth.json", "api_key", "secret", "@example.com", "c:\\users", "/home/"):
        assert forbidden not in content
    assert "inv_demo_" in content and "txn_demo_" in content
