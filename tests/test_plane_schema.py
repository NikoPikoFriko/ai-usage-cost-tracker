"""Multi-provider plane schema + rollup honesty."""

from pathlib import Path

from src.db import TrackerDB
from src.export_web import build_dashboard_payload
from src.models import UsageEvent


def test_subscription_row_nullable_tokens_and_by_rail(tmp_path: Path):
    db_path = tmp_path / "t.db"
    db = TrackerDB(db_path)
    events = [
        UsageEvent(
            event_id="e-metered",
            source_product="codex",
            session_id="s1",
            ts_utc="2026-08-10T12:00:00Z",
            model="gpt-5.6-terra",
            grain="turn",
            money_rail="api_metered",
            input_tokens=1000,
            output_tokens=100,
            cost_usd=0.05,
            evidence_class="OBS",
            ingest_channel="test",
            label="turn-1",
        ),
        UsageEvent(
            event_id="e-sub",
            source_product="chatgpt",
            session_id="s-sub",
            ts_utc="2026-08-01T00:00:00Z",
            model="subscription",
            grain="subscription_period",
            money_rail="subscription",
            input_tokens=None,
            output_tokens=None,
            cost_usd=20.0,
            evidence_class="OBS",
            ingest_channel="chatgpt_subscription",
            label="plus-seat-august",
        ),
    ]
    db.upsert_events(events)
    db.upsert_session_meta(
        {
            "session_id": "s1",
            "title": "work",
            "source_product": "codex",
            "source_surface": "cli",
            "cwd": None,
            "started_at": "2026-08-10T12:00:00Z",
            "model_default": "gpt-5.6-terra",
            "originator": None,
        }
    )
    payload = build_dashboard_payload(db)
    assert payload["totals"]["cost_by_rail"]["api_metered"] == 0.05
    assert payload["totals"]["cost_by_rail"]["subscription"] == 20.0
    assert payload["totals"]["cost_usd_metered_only"] == 0.05
    # grand priced sum includes both rails — UI default by_rail shows chips
    assert payload["totals"]["cost_usd_priced"] == 20.05
    assert "chatgpt" in payload["totals"]["providers"]
    assert "codex" in payload["totals"]["providers"]
    db.close()
