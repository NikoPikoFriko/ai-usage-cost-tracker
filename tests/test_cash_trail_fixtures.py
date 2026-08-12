from __future__ import annotations

import csv
from datetime import date
from pathlib import Path


FIXTURES = Path(__file__).parent / "fixtures"


def _rows(name: str) -> list[dict[str, str]]:
    with (FIXTURES / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_cash_trail_fixtures_are_synthetic_and_cross_reference_cleanly():
    invoices = _rows("cash_trail_invoice_sample.csv")
    bank = _rows("cash_trail_bank_sample.csv")
    links = _rows("cash_trail_links_sample.csv")

    assert len(invoices) == 2
    assert len(bank) == 2
    assert len(links) == 1

    assert all(row["source_record_id"].startswith("inv_demo_") for row in invoices)
    assert all(row["source_record_id"].startswith("txn_demo_") for row in bank)
    assert all(row["link_id"].startswith("link_demo_") for row in links)

    link = links[0]
    assert link["relation"] == "settles"
    assert link["status"] == "confirmed"
    assert link["confirmed_by"] == "operator"

    invoice = next(
        row
        for row in invoices
        if row["source_record_id"] == link["invoice_source_record_id"]
    )
    settlement = next(
        row
        for row in bank
        if row["source_record_id"] == link["settlement_source_record_id"]
    )

    assert invoice["amount_usd"] == settlement["amount_usd"]
    assert invoice["currency"] == settlement["currency"] == "USD"
    assert settlement["direction"] == "debit"
    assert settlement["status"] == "posted"

    invoice_day = date.fromisoformat(invoice["invoice_date"])
    posted_day = date.fromisoformat(settlement["posted_date"])
    assert 0 <= (posted_day - invoice_day).days <= 3

    linked_invoice_ids = {row["invoice_source_record_id"] for row in links}
    assert any(
        row["source_record_id"] not in linked_invoice_ids for row in invoices
    ), "fixture must retain an unresolved invoice candidate"

    fixture_text = "\n".join(
        ",".join(row.values()) for row in invoices + bank + links
    ).lower()
    for forbidden in ("auth.json", "api_key", "secret", "@example.com", "c:\\users"):
        assert forbidden not in fixture_text
