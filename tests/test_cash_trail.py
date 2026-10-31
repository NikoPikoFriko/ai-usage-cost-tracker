from __future__ import annotations

import csv
from pathlib import Path

from src.cash_trail import import_cash_trail
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
    db.upsert_cash_link({**link, "status": "confirmed", "confirmed_by": "operator"})
    assert [row[0] for row in db.conn.execute(
        "SELECT status FROM cash_link_history ORDER BY history_id"
    )] == ["candidate", "confirmed"]
    db.close()


def test_native_currency_pending_and_partial_settlement_are_explicit(tmp_path: Path):
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
