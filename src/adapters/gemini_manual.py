"""Google Gemini provider — subscription/API budget amortization + optional usage CSV."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from src.adapters.base import IngestResult
from src.adapters.manual_common import (
    parse_usage_csv,
    session_meta_for_sub,
    subscription_event,
)

CHANNEL_ID = "gemini_manual"


class GeminiManualAdapter:
    id = CHANNEL_ID
    product = "gemini"
    description = (
        "Gemini / Google AI seat or prepaid budget amortization + optional "
        "usage/export CSV (token MAXres when columns present)"
    )

    def run(
        self,
        monthly_usd: Optional[float] = None,
        period: Optional[str] = None,
        csv_path: Optional[Path] = None,
        **_: Any,
    ) -> IngestResult:
        events = []
        metas = []
        stats: dict[str, Any] = {"files_seen": 0, "events": 0, "mode": []}

        if monthly_usd is not None:
            if not period:
                raise ValueError("--period YYYY-MM required with --monthly-usd")
            events.append(
                subscription_event(
                    product="gemini",
                    channel=CHANNEL_ID,
                    period=period,
                    monthly_usd=float(monthly_usd),
                    label=f"gemini-seat-{period}",
                    notes="Seat or budget amortization — not a substitute for API token export",
                )
            )
            metas.append(session_meta_for_sub("gemini", period))
            stats["mode"].append("subscription")

        if csv_path is not None:
            p = Path(csv_path)
            if not p.is_file():
                raise FileNotFoundError(p)
            rows = parse_usage_csv(
                p,
                product="gemini",
                channel=CHANNEL_ID,
                default_rail="api_metered",
                default_grain="request",
            )
            # If CSV has tokens but no cost, leave GAP for reprice when rates exist
            events.extend(rows)
            stats["files_seen"] += 1
            stats["mode"].append("csv")
            stats["csv_path"] = str(p)

        if not events:
            raise ValueError(
                "Provide --monthly-usd + --period and/or --csv path for Gemini ingest"
            )

        stats["events"] = len(events)
        return IngestResult(events=events, session_metas=metas, stats=stats)
