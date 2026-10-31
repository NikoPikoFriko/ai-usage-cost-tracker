"""Local-only import and reconciliation for invoice and bank cash evidence."""

from __future__ import annotations

import csv
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from src.adapters.base import stable_hash
from src.db import TrackerDB
from src.models import UsageEvent

CHANNEL = "cash-trail-manual"
_CURRENCY = re.compile(r"^[A-Z]{3}$")


def _read_rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = required - fields
        if missing:
            raise ValueError(f"{path}: missing CSV columns: {', '.join(sorted(missing))}")
        return list(reader)


def _amount(raw: str, *, path: Path, row_number: int) -> Decimal:
    try:
        value = Decimal(raw.strip())
    except (InvalidOperation, AttributeError):
        raise ValueError(f"{path}: row {row_number}: invalid amount {raw!r}") from None
    if not value.is_finite():
        raise ValueError(f"{path}: row {row_number}: amount must be finite")
    return value


def _date(raw: str, *, path: Path, row_number: int) -> str:
    try:
        return date.fromisoformat(raw.strip()).isoformat()
    except ValueError:
        raise ValueError(
            f"{path}: row {row_number}: date must use YYYY-MM-DD"
        ) from None


def _currency(raw: str, *, path: Path, row_number: int) -> str:
    value = raw.strip().upper()
    if not _CURRENCY.fullmatch(value):
        raise ValueError(f"{path}: row {row_number}: currency must be a 3-letter code")
    return value


def _event(
    *,
    source_id: str,
    source_product: str,
    surface: str,
    day: str,
    amount: Decimal,
    currency: str,
    merchant: str,
    status: str,
    path: Path,
    kind: str,
) -> UsageEvent:
    if not source_id.strip():
        raise ValueError(f"{path}: source_record_id must not be empty")
    native_amount = float(amount)
    normalized_amount = format(amount.normalize(), "f")
    event_id = stable_hash(CHANNEL, kind, source_id, normalized_amount, currency, day)
    return UsageEvent(
        event_id=event_id,
        source_product=source_product or "unknown_ai",
        source_surface=surface,
        session_id=f"cash-{kind}-{event_id[:12]}",
        ts_utc=f"{day}T00:00:00+00:00",
        model="cash_evidence",
        grain="day",
        money_rail="invoice_line",
        input_tokens=None,
        output_tokens=None,
        cached_input_tokens=None,
        reasoning_tokens=None,
        cache_write_input_tokens=None,
        total_tokens=None,
        cost_usd=native_amount if currency == "USD" else None,
        amount_native=native_amount,
        currency=currency,
        evidence_class="CAND" if status == "pending" else "OBS",
        ingest_channel=CHANNEL,
        raw_ref=f"{path}#{source_id}",
        label=f"{kind} line",
        cash_source_record_id=source_id,
        cash_status=status,
        cash_merchant=merchant.strip() or None,
    )


def _invoice_events(path: Path) -> list[UsageEvent]:
    rows = _read_rows(
        path,
        {"source_record_id", "source_product", "invoice_date", "currency"},
    )
    out = []
    seen: set[str] = set()
    for number, row in enumerate(rows, start=2):
        source_id = row["source_record_id"].strip()
        if source_id in seen:
            raise ValueError(f"{path}: row {number}: duplicate source_record_id {source_id!r}")
        seen.add(source_id)
        date_field = row["invoice_date"]
        day = _date(date_field, path=path, row_number=number)
        currency = _currency(row["currency"], path=path, row_number=number)
        raw_amount = (row.get("amount_native") or row.get("amount_usd") or row.get("amount") or "").strip()
        if not raw_amount:
            raise ValueError(f"{path}: row {number}: amount_native or amount_usd is required")
        amount = _amount(raw_amount, path=path, row_number=number)
        status = (row.get("status") or "invoiced").strip().lower()
        if status not in {"invoiced", "credit_note"}:
            raise ValueError(f"{path}: row {number}: invoice status must be invoiced or credit_note")
        if status == "credit_note" and amount > 0:
            amount = -amount
        out.append(
            _event(
                source_id=source_id,
                source_product=row["source_product"].strip() or "unknown_ai",
                surface="provider_invoice",
                day=day,
                amount=amount,
                currency=currency,
                merchant=row.get("merchant", ""),
                status="posted",
                path=path,
                kind="invoice",
            )
        )
    return out


def _bank_events(path: Path) -> list[UsageEvent]:
    rows = _read_rows(path, {"source_record_id", "currency", "direction", "status"})
    out = []
    seen: set[str] = set()
    for number, row in enumerate(rows, start=2):
        source_id = row["source_record_id"].strip()
        if source_id in seen:
            raise ValueError(f"{path}: row {number}: duplicate source_record_id {source_id!r}")
        seen.add(source_id)
        day_raw = (row.get("posted_date") or row.get("date") or "").strip()
        day = _date(day_raw, path=path, row_number=number)
        currency = _currency(row["currency"], path=path, row_number=number)
        raw_amount = (row.get("amount_native") or row.get("amount_usd") or row.get("amount") or "").strip()
        if not raw_amount:
            raise ValueError(f"{path}: row {number}: amount_native or amount_usd is required")
        amount = abs(_amount(raw_amount, path=path, row_number=number))
        direction = row["direction"].strip().lower()
        if direction not in {"debit", "credit"}:
            raise ValueError(f"{path}: row {number}: direction must be debit or credit")
        if direction == "credit":
            amount = -amount
        status = row["status"].strip().lower()
        if status not in {"posted", "pending"}:
            raise ValueError(f"{path}: row {number}: status must be posted or pending")
        out.append(
            _event(
                source_id=source_id,
                source_product=(row.get("source_product") or "unknown_ai").strip(),
                surface="bank_statement",
                day=day,
                amount=amount,
                currency=currency,
                merchant=row.get("descriptor") or row.get("merchant") or "",
                status=status,
                path=path,
                kind="bank",
            )
        )
    return out


def _source_map(db: TrackerDB) -> dict[str, str]:
    rows = db.conn.execute(
        """
        SELECT cash_source_record_id, event_id FROM usage_events
        WHERE ingest_channel=? AND cash_source_record_id IS NOT NULL
        ORDER BY rowid
        """,
        (CHANNEL,),
    ).fetchall()
    out: dict[str, str] = {}
    for row in rows:
        out[row["cash_source_record_id"]] = row["event_id"]
    return out


def _link_id(invoice_id: str, settlement_id: str, relation: str) -> str:
    return stable_hash(invoice_id, settlement_id, relation)


def _link(
    invoice_id: str,
    settlement_id: str,
    relation: str,
    status: str,
    confidence: float | None,
    matched_on: str,
    confirmed_by: str | None,
) -> dict[str, Any]:
    return {
        "link_id": _link_id(invoice_id, settlement_id, relation),
        "invoice_event_id": invoice_id,
        "settlement_event_id": settlement_id,
        "relation": relation,
        "status": status,
        "confidence": confidence,
        "matched_on": matched_on,
        "confirmed_by": confirmed_by,
    }


def _import_links(
    path: Path, source_ids: dict[str, str], surfaces: dict[str, str]
) -> list[dict[str, Any]]:
    rows = _read_rows(
        path,
        {
            "invoice_source_record_id",
            "settlement_source_record_id",
            "relation",
            "status",
            "confirmed_by",
            "matched_on",
        },
    )
    links = []
    for number, row in enumerate(rows, start=2):
        try:
            invoice_id = source_ids[row["invoice_source_record_id"].strip()]
            settlement_id = source_ids[row["settlement_source_record_id"].strip()]
        except KeyError as exc:
            raise ValueError(
                f"{path}: row {number}: unknown source_record_id {exc.args[0]!r}"
            ) from None
        status = row["status"].strip().lower()
        relation = row["relation"].strip().lower()
        if relation not in {
            "settles", "refunds", "partial_settlement", "candidate_match"
        }:
            raise ValueError(f"{path}: row {number}: invalid relation {relation!r}")
        if status not in {"candidate", "confirmed", "rejected"}:
            raise ValueError(f"{path}: row {number}: invalid status {status!r}")
        if surfaces.get(invoice_id) != "provider_invoice":
            raise ValueError(f"{path}: row {number}: invoice ID is not invoice evidence")
        if surfaces.get(settlement_id) != "bank_statement":
            raise ValueError(f"{path}: row {number}: settlement ID is not bank evidence")
        confirmed_by = row["confirmed_by"].strip() or None
        if status == "confirmed" and confirmed_by != "operator" and not (
            confirmed_by or ""
        ).startswith("rule:"):
            raise ValueError(
                f"{path}: row {number}: confirmed links require operator or rule:<id>"
            )
        if status == "confirmed" and confirmed_by == "rule:":
            raise ValueError(f"{path}: row {number}: deterministic rule ID is required")
        links.append(
            _link(
                invoice_id,
                settlement_id,
                relation,
                status,
                None,
                row["matched_on"].strip(),
                confirmed_by,
            )
        )
    return links


def _candidate_links(db: TrackerDB) -> list[dict[str, Any]]:
    events = db.fetch_all_events()
    invoices = [
        event
        for event in events
        if event.get("source_surface") == "provider_invoice"
        and event.get("money_rail") == "invoice_line"
    ]
    banks = [
        event
        for event in events
        if event.get("source_surface") == "bank_statement"
        and event.get("money_rail") == "invoice_line"
        and event.get("cash_status") == "posted"
    ]
    existing = {
        (link["invoice_event_id"], link["settlement_event_id"])
        for link in db.fetch_cash_links()
    }
    candidates = []
    for invoice in invoices:
        for bank in banks:
            pair = (invoice["event_id"], bank["event_id"])
            if pair in existing:
                continue
            currency = (invoice.get("currency") or "").upper()
            if not currency or currency != (bank.get("currency") or "").upper():
                continue
            invoice_amount = invoice.get("amount_native")
            bank_amount = bank.get("amount_native")
            if invoice_amount is None or bank_amount is None:
                continue
            if invoice_amount * bank_amount < 0:
                continue
            invoice_day = date.fromisoformat(invoice["ts_utc"][:10])
            bank_day = date.fromisoformat(bank["ts_utc"][:10])
            day_gap = abs((bank_day - invoice_day).days)
            merchant_a = (invoice.get("cash_merchant") or "").lower()
            merchant_b = (bank.get("cash_merchant") or "").lower()
            merchant_score = SequenceMatcher(None, merchant_a, merchant_b).ratio()
            exact_amount = abs(Decimal(str(invoice_amount))) == abs(Decimal(str(bank_amount)))
            if day_gap <= 14 and (
                (exact_amount and merchant_score >= 0.35) or merchant_score >= 0.62
            ):
                candidates.append(
                    _link(
                        invoice["event_id"],
                        bank["event_id"],
                        "candidate_match",
                        "candidate",
                        round(0.65 if exact_amount else merchant_score, 3),
                        "currency,date_window,merchant" + (",amount" if exact_amount else ""),
                        None,
                    )
                )
    return candidates


def import_cash_trail(
    db: TrackerDB,
    *,
    invoice_csv: Path | None = None,
    bank_csv: Path | None = None,
    links_csv: Path | None = None,
) -> dict[str, int]:
    """Validate all supplied files, then idempotently import events and links."""
    if not any((invoice_csv, bank_csv, links_csv)):
        raise ValueError("Provide at least one of --invoices, --bank, or --links")
    invoices = _invoice_events(invoice_csv) if invoice_csv else []
    banks = _bank_events(bank_csv) if bank_csv else []
    events = invoices + banks
    source_ids: dict[str, str] = {}
    for event in events:
        assert event.cash_source_record_id is not None
        source_id = event.cash_source_record_id
        if source_id in source_ids:
            raise ValueError(f"Duplicate cash source_record_id across files: {source_id}")
        source_ids[source_id] = event.event_id

    # Validate that link files resolve before writing any event rows.
    existing_sources = _source_map(db)
    event_surfaces = {
        row["event_id"]: row["source_surface"]
        for row in db.conn.execute(
            "SELECT event_id, source_surface FROM usage_events WHERE ingest_channel=?",
            (CHANNEL,),
        ).fetchall()
    }
    if events:
        existing_rows = db.conn.execute(
            """
            SELECT cash_source_record_id, event_id, source_surface FROM usage_events
            WHERE ingest_channel=? AND cash_source_record_id IS NOT NULL
            """,
            (CHANNEL,),
        ).fetchall()
        existing_surfaces: dict[str, set[str]] = {}
        for row in existing_rows:
            existing_surfaces.setdefault(row["cash_source_record_id"], set()).add(
                row["source_surface"]
            )
        for event in events:
            known_surfaces = existing_surfaces.get(
                event.cash_source_record_id or "", set()
            )
            if known_surfaces and event.source_surface not in known_surfaces:
                raise ValueError(
                    "Invoice and bank source_record_id values must be distinct: "
                    f"{event.cash_source_record_id}"
                )
            event_surfaces[event.event_id] = event.source_surface
    source_ids = {**existing_sources, **source_ids}
    explicit_links = (
        _import_links(links_csv, source_ids, event_surfaces) if links_csv else []
    )

    db.upsert_events(events)
    for link in explicit_links:
        db.upsert_cash_link(link)
    candidates = _candidate_links(db)
    for link in candidates:
        db.upsert_cash_link(link)
    return {
        "invoices": len(invoices),
        "bank_rows": len(banks),
        "links_imported": len(explicit_links),
        "candidate_links": len(candidates),
    }
