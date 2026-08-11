"""Build web/data.json from SQLite for MAXres multi-provider dashboard."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
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


def build_dashboard_payload(db: TrackerDB) -> dict[str, Any]:
    events_raw = db.fetch_all_events()
    meta_map = db.fetch_session_meta()

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
            "grade": e.get("evidence_class") or "CAND",
            "gap_code": "G-NO-PRICE" if e.get("cost_usd") is None else None,
            "ingest_channel": e.get("ingest_channel"),
            "billing_identity": e.get("billing_identity"),
            "service_tier": e.get("service_tier"),
        }
        events_out.append(row)
        by_session[e["session_id"]].append(row)
        if row["cost_usd"] is not None:
            by_rail[rail] += float(row["cost_usd"])
            by_product[product] += float(row["cost_usd"])

    sessions_out = []
    for sid, evs in by_session.items():
        sm = meta_map.get(sid, {})
        tin = sum(x["tokens_in"] for x in evs)
        tout = sum(x["tokens_out"] for x in evs)
        tcached = sum(x["tokens_cached"] for x in evs)
        priced = [x for x in evs if x["cost_usd"] is not None]
        cost = sum(x["cost_usd"] for x in priced) if priced else None
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
                "model_mix": models,
                "grade": _worst_grade(grades),
                "coverage": f"{len(priced)}/{len(evs)}",
                "money_rails": rails,
            }
        )

    sessions_out.sort(
        key=lambda s: (s["cost_usd"] is None, -(s["cost_usd"] or 0), s.get("started_at") or ""),
    )

    all_priced = [e for e in events_out if e["cost_usd"] is not None]
    unpriced = [e for e in events_out if e["cost_usd"] is None]
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
