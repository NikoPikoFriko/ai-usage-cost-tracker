"""Build web/data.json from SQLite for MAXres multi-provider dashboard."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.db import TrackerDB


def _worst_grade(grades: list[str]) -> str:
    order = {"GAP": 4, "HYP": 3, "CAND": 2, "NIKO": 1, "OBS": 0}
    if not grades:
        return "CAND"
    return max(grades, key=lambda g: order.get(g, 0))


def _role_for(product: str) -> str:
    if product == "codex":
        return "cli"
    if product == "grok":
        return "agent"
    return "assistant"


def _cash_trail_payload(
    events: list[dict[str, Any]], links: list[dict[str, Any]]
) -> dict[str, Any]:
    cash_events = [
        event
        for event in events
        if event.get("money_rail") == "invoice_line"
        and event.get("source_surface") in {"provider_invoice", "bank_statement"}
        and event.get("cash_superseded_by") is None
    ]
    by_id = {event["event_id"]: event for event in cash_events}
    confirmed_invoice_ids = set()
    for link in links:
        settlement = by_id.get(link["settlement_event_id"])
        invoice = by_id.get(link["invoice_event_id"])
        if (
            link["status"] == "confirmed"
            and link["relation"] in {"settles", "refunds", "partial_settlement"}
            and settlement
            and invoice
            and invoice.get("cash_superseded_by") is None
            and settlement.get("cash_status") == "posted"
        ):
            confirmed_invoice_ids.add(link["invoice_event_id"])

    totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "lower": 0.0,
            "upper": 0.0,
            "pending": 0.0,
            "unresolved_invoices": 0,
            "partial_remainders": 0,
        }
    )
    unresolved = []
    pending_count = 0
    for event in cash_events:
        currency = (event.get("currency") or ("USD" if event.get("cost_usd") is not None else "UNK")).upper()
        amount_value = event.get("amount_native")
        if amount_value is None:
            amount_value = event.get("cost_usd")
        amount = Decimal(str(amount_value or 0))
        bucket = totals[currency]
        if event.get("source_surface") == "bank_statement":
            if event.get("cash_status") == "pending":
                pending_count += 1
                bucket["pending"] += float(amount)
            else:
                bucket["lower"] += float(amount)
                bucket["upper"] += float(amount)
        elif event["event_id"] not in confirmed_invoice_ids:
            bucket["upper" if amount >= 0 else "lower"] += float(amount)
            bucket["unresolved_invoices"] += 1
            unresolved.append(
                {
                    "event_id": event["event_id"],
                    "currency": currency,
                    "amount_native": float(amount),
                    "date": event["ts_utc"][:10],
                }
            )

    partial_settlements: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for link in links:
        if (
            link["status"] == "confirmed"
            and link["relation"] == "partial_settlement"
            and link["invoice_event_id"] in by_id
            and link["settlement_event_id"] in by_id
        ):
            partial_settlements[link["invoice_event_id"]].append(link)
    for invoice_id, invoice_links in partial_settlements.items():
        invoice = by_id.get(invoice_id)
        if not invoice:
            continue
        posted_settlements = [
            by_id.get(link["settlement_event_id"])
            for link in invoice_links
        ]
        posted_settlements = [
            row for row in posted_settlements
            if row and row.get("cash_status") == "posted"
        ]
        if not posted_settlements:
            continue
        currency = (invoice.get("currency") or "UNK").upper()
        invoice_amount = Decimal(
            str(invoice.get("amount_native") or invoice.get("cost_usd") or 0)
        )
        settlement_amount = sum(
            (
                Decimal(str(row.get("amount_native") or row.get("cost_usd") or 0))
                for row in posted_settlements
            ),
            Decimal(0),
        )
        bucket = totals[currency]
        remainder = invoice_amount - settlement_amount
        if remainder:
            if abs(remainder) >= Decimal("0.000001"):
                bucket["upper" if remainder >= 0 else "lower"] += float(remainder)
                bucket["partial_remainders"] += 1

    ranges = [
        {
            "currency": currency,
            "lower": round(values["lower"], 6),
            "upper": round(values["upper"], 6),
            "pending": round(values["pending"], 6),
            "unresolved_invoices": values["unresolved_invoices"],
            "partial_remainders": values["partial_remainders"],
        }
        for currency, values in sorted(totals.items())
    ]
    return {
        "ranges": ranges,
        "links": [
            {
                "link_id": link["link_id"],
                "invoice_event_id": link["invoice_event_id"],
                "settlement_event_id": link["settlement_event_id"],
                "relation": link["relation"],
                "status": link["status"],
                "confidence": link["confidence"],
                "matched_on": link["matched_on"],
                "confirmed_by": link["confirmed_by"],
            }
            for link in links
        ],
        "unresolved_invoices": unresolved,
        "pending_count": pending_count,
    }


def build_dashboard_payload(db: TrackerDB) -> dict[str, Any]:
    events_raw = db.fetch_all_events()
    meta_map = db.fetch_session_meta()
    cash_trail = _cash_trail_payload(events_raw, db.fetch_cash_links())
    supporting_event_ids = {
        link["invoice_event_id"]
        for link in cash_trail["links"]
        if link["status"] == "confirmed"
        and link["relation"] in {"settles", "refunds", "partial_settlement"}
        and link["invoice_event_id"] in {
            event["event_id"]
            for event in events_raw
            if event.get("cash_superseded_by") is None
        }
    }

    events_out = []
    by_session: dict[str, list[dict]] = defaultdict(list)
    by_rail: dict[str, float] = defaultdict(float)
    by_product: dict[str, float] = defaultdict(float)
    products: set[str] = set()

    for e in events_raw:
        product = e.get("source_product") or "unknown"
        rail = e.get("money_rail") or "unknown"
        grain = e.get("grain") or "unknown"
        products.add(product)
        row = {
            "event_id": e["event_id"],
            "session_id": e["session_id"],
            "channel": product,
            "ts": e["ts_utc"],
            "label": e.get("label") or "turn",
            "role": _role_for(product),
            "model": e["model"],
            "grain": grain,
            "money_rail": rail,
            "tokens_in": e["input_tokens"] if e["input_tokens"] is not None else 0,
            "tokens_out": e["output_tokens"] if e["output_tokens"] is not None else 0,
            "tokens_cached": e.get("cached_input_tokens") or 0,
            "cost_usd": e.get("cost_usd"),
            "amount_native": e.get("amount_native"),
            "currency": e.get("currency"),
            "cash_status": e.get("cash_status"),
            "cash_supporting_only": e["event_id"] in supporting_event_ids,
            "cash_source_surface": e.get("source_surface"),
            "cash_current": e.get("cash_superseded_by") is None,
            "grade": e.get("evidence_class") or "CAND",
            "gap_code": (
                "G-NO-PRICE"
                if e.get("cost_usd") is None and e.get("amount_native") is None
                else None
            ),
            "ingest_channel": e.get("ingest_channel"),
            "billing_identity": e.get("billing_identity"),
            "service_tier": e.get("service_tier"),
        }
        events_out.append(row)
        by_session[e["session_id"]].append(row)
        if (
            row["cost_usd"] is not None
            and not row["cash_supporting_only"]
            and row["cash_current"]
        ):
            by_rail[rail] += float(row["cost_usd"])
            by_product[product] += float(row["cost_usd"])

    sessions_out = []
    for sid, evs in by_session.items():
        sm = meta_map.get(sid, {})
        tin = sum(x["tokens_in"] for x in evs)
        tout = sum(x["tokens_out"] for x in evs)
        tcached = sum(x["tokens_cached"] for x in evs)
        priced = [
            x for x in evs
            if x["cost_usd"] is not None
            and not x["cash_supporting_only"]
            and x["cash_current"]
        ]
        cost = sum(x["cost_usd"] for x in priced) if priced else None
        native_cash = [
            x for x in evs
            if x["amount_native"] is not None
            and x["currency"]
            and not x["cash_supporting_only"]
            and x["cash_current"]
        ]
        native_currencies = {x["currency"] for x in native_cash}
        native_amount = (
            round(sum(float(x["amount_native"]) for x in native_cash), 6)
            if len(native_currencies) == 1
            else None
        )
        models = sorted({x["model"] for x in evs if x.get("model")})
        grades = [x["grade"] for x in evs]
        rails = sorted({x.get("money_rail") or "unknown" for x in evs})
        ts_list = [x["ts"] for x in evs if x.get("ts")]
        started = sm.get("started_at") or (min(ts_list) if ts_list else None)
        ended = max(ts_list) if ts_list else None
        title = sm.get("title") or sid[:12]
        channel = evs[0]["channel"] if evs else sm.get("source_product") or "unknown"
        sessions_out.append(
            {
                "session_id": sid,
                "channel": channel,
                "title": title,
                "started_at": started,
                "ended_at": ended,
                "events_n": len(evs),
                "tokens_in": tin,
                "tokens_out": tout,
                "tokens_cached": tcached,
                "cost_usd": None if cost is None else round(cost, 6),
                "amount_native": native_amount,
                "currency": next(iter(native_currencies)) if len(native_currencies) == 1 else None,
                "cash_multi_currency": len(native_currencies) > 1,
                "cash_supporting_only": bool(evs) and all(
                    x["cash_supporting_only"] for x in evs
                ),
                "cash_current": any(x["cash_current"] for x in evs),
                "model_mix": models,
                "grade": _worst_grade(grades),
                "coverage": f"{sum(x['cash_current'] and (x['cost_usd'] is not None or x['amount_native'] is not None) for x in evs)}/{len(evs)}",
                "money_rails": rails,
            }
        )

    sessions_out.sort(
        key=lambda s: (s["cost_usd"] is None, -(s["cost_usd"] or 0), s.get("started_at") or ""),
    )

    all_priced = [
        e for e in events_out
        if e["cost_usd"] is not None
        and not e["cash_supporting_only"]
        and e["cash_current"]
    ]
    unpriced = [
        e for e in events_out
        if e["cost_usd"] is None
        and e["amount_native"] is None
        and not e["cash_supporting_only"]
        and e["cash_current"]
    ]
    metered = [e for e in all_priced if e.get("money_rail") == "api_metered"]
    credits = [e for e in all_priced if e.get("money_rail") == "credits"]

    totals = {
        "cost_usd_priced": round(sum(e["cost_usd"] for e in all_priced), 6),
        "cost_usd_metered_only": round(sum(e["cost_usd"] for e in metered), 6),
        "cost_usd_credits": round(sum(e["cost_usd"] for e in credits), 6),
        "cost_by_rail": {k: round(v, 6) for k, v in sorted(by_rail.items())},
        "cost_by_product": {k: round(v, 6) for k, v in sorted(by_product.items())},
        "cost_usd_unknown_events": len(unpriced),
        "tokens_in": sum(e["tokens_in"] for e in events_out),
        "tokens_out": sum(e["tokens_out"] for e in events_out),
        "tokens_cached": sum(e["tokens_cached"] for e in events_out),
        "sessions_n": len(sessions_out),
        "events_n": len(events_out),
        "events_priced_n": len(all_priced),
        "cash_native_events_n": sum(
            e["amount_native"] is not None and e["currency"] != "USD"
            for e in events_out
        ),
        "providers": sorted(products),
    }

    gaps = []
    if unpriced:
        gaps.append(
            {
                "code": "G-NO-PRICE",
                "count": len(unpriced),
                "example_event_id": unpriced[0]["event_id"],
                "action": "Add model rate to config/PRICING_MODELS.csv then: python -m src.cli reprice",
            }
        )

    return {
        "meta": {
            "contract_id": "FC-2026-08-10-AI-USAGE-COST",
            "plane": "multi-provider",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data_class": "LIVE" if events_out else "EMPTY",
            "currency": "USD",
            "price_table_version": "config/PRICING_MODELS.csv",
            "privacy": "labels only — no prompt bodies",
            "rollup_default": "by_rail",
            "note": "N-way ledger: do not treat mixed rails as one invoice. credits ≈ rate-card estimate for plan burn.",
        },
        "totals": totals,
        "cash_trail": cash_trail,
        "sessions": sessions_out,
        "events": events_out,
        "gaps": gaps,
    }


def write_web_data(db_path: Path, out_path: Path) -> dict[str, Any]:
    db = TrackerDB(db_path)
    try:
        payload = build_dashboard_payload(db)
    finally:
        db.close()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
