"""Shared helpers for subscription + manual CSV provider adapters."""

from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.adapters.base import stable_hash
from src.models import UsageEvent


def month_bounds(period: str) -> tuple[str, str, str]:
    """period YYYY-MM → (start_iso, end_iso, period_id)."""
    y, m = period.split("-")
    y_i, m_i = int(y), int(m)
    start = date(y_i, m_i, 1)
    if m_i == 12:
        end = date(y_i + 1, 1, 1)
    else:
        end = date(y_i, m_i + 1, 1)
    return (
        start.isoformat() + "T00:00:00+00:00",
        end.isoformat() + "T00:00:00+00:00",
        period,
    )


def subscription_event(
    *,
    product: str,
    channel: str,
    period: str,
    monthly_usd: float,
    label: Optional[str] = None,
    notes: Optional[str] = None,
) -> UsageEvent:
    start, _, pid = month_bounds(period)
    # Period-stable id so correcting --monthly-usd updates the seat row
    # instead of inserting a second subscription_period event.
    eid = stable_hash(channel, product, "subscription", pid)
    return UsageEvent(
        event_id=eid,
        source_product=product,
        source_surface="billing",
        session_id=f"{product}-sub-{pid}",
        ts_utc=start,
        model="subscription",
        grain="subscription_period",
        money_rail="subscription",
        input_tokens=None,
        output_tokens=None,
        cost_usd=float(monthly_usd),
        evidence_class="OBS",
        ingest_channel=channel,
        billing_identity="seat",
        label=label or f"{product}-seat-{pid}",
        notes=notes or f"Monthly seat amortization for {pid}",
    )


def parse_usage_csv(
    path: Path,
    *,
    product: str,
    channel: str,
    default_rail: str = "invoice_line",
    default_grain: str = "day",
) -> list[UsageEvent]:
    """
    CSV columns (header required):
      ts_utc, model, cost_usd
    optional: session_id, input_tokens, output_tokens, money_rail, grain, label, notes
    """
    events: list[UsageEvent] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return events
        for i, row in enumerate(reader):
            ts = (row.get("ts_utc") or row.get("date") or "").strip()
            if not ts:
                continue
            if "T" not in ts:
                ts = ts + "T00:00:00+00:00"
            model = (row.get("model") or "unknown").strip()
            cost_raw = (row.get("cost_usd") or row.get("amount") or "").strip()
            cost = float(cost_raw) if cost_raw else None
            tin = row.get("input_tokens")
            tout = row.get("output_tokens")
            session_id = (row.get("session_id") or f"{product}-csv-{path.stem}").strip()
            rail = (row.get("money_rail") or default_rail).strip()
            grain = (row.get("grain") or default_grain).strip()
            label = (row.get("label") or f"row-{i+1}").strip()
            eid = stable_hash(
                channel,
                product,
                session_id,
                ts,
                model,
                cost_raw or "",
                str(i),
            )
            events.append(
                UsageEvent(
                    event_id=eid,
                    source_product=product,
                    source_surface="csv",
                    session_id=session_id,
                    ts_utc=ts,
                    model=model,
                    grain=grain,
                    money_rail=rail,
                    input_tokens=int(tin) if tin not in (None, "") else None,
                    output_tokens=int(tout) if tout not in (None, "") else None,
                    cost_usd=cost,
                    evidence_class="OBS" if cost is not None else "GAP",
                    ingest_channel=channel,
                    raw_ref=str(path),
                    label=label,
                    notes=(row.get("notes") or None),
                )
            )
    return events


def session_meta_for_sub(product: str, period: str) -> dict[str, Any]:
    start, _, pid = month_bounds(period)
    return {
        "session_id": f"{product}-sub-{pid}",
        "title": f"{product} subscription {pid}",
        "source_product": product,
        "source_surface": "billing",
        "cwd": None,
        "started_at": start,
        "model_default": "subscription",
        "originator": None,
    }
