from pathlib import Path

from src.adapters.gemini_manual import GeminiManualAdapter
from src.adapters.perplexity_manual import PerplexityManualAdapter
from src.adapters.registry import get_adapter, list_adapters
from src.db import TrackerDB
from src.export_web import build_dashboard_payload

ROOT = Path(__file__).resolve().parents[1]


def test_registry_lists_three_providers():
    ids = {a["cli_id"] for a in list_adapters()}
    assert "codex-jsonl" in ids
    assert "perplexity-manual" in ids
    assert "gemini-manual" in ids


def test_perplexity_subscription(tmp_path: Path):
    ad = PerplexityManualAdapter()
    res = ad.run(monthly_usd=20.0, period="2026-08")
    assert len(res.events) == 1
    e = res.events[0]
    assert e.source_product == "perplexity"
    assert e.money_rail == "subscription"
    assert e.grain == "subscription_period"
    assert e.cost_usd == 20.0
    assert e.input_tokens is None


def test_subscription_reingest_updates_amount(tmp_path: Path):
    """Correcting --monthly-usd must update the seat row, not double-count."""
    ad = PerplexityManualAdapter()
    db = TrackerDB(tmp_path / "t.db")
    first = ad.run(monthly_usd=20.0, period="2026-08")
    second = ad.run(monthly_usd=22.0, period="2026-08")
    assert first.events[0].event_id == second.events[0].event_id
    db.upsert_events(first.events)
    db.upsert_events(second.events)
    payload = build_dashboard_payload(db)
    assert payload["totals"]["events_n"] == 1
    assert payload["totals"]["cost_by_rail"]["subscription"] == 22.0
    db.close()


def test_gemini_csv(tmp_path: Path):
    ad = GeminiManualAdapter()
    csv_path = ROOT / "tests" / "fixtures" / "gemini_sample.csv"
    res = ad.run(csv_path=csv_path)
    assert len(res.events) == 2
    assert all(e.source_product == "gemini" for e in res.events)
    assert res.events[0].money_rail == "api_metered"


def test_plane_export_multi_provider(tmp_path: Path):
    db = TrackerDB(tmp_path / "t.db")
    p = PerplexityManualAdapter().run(monthly_usd=20.0, period="2026-08")
    g = GeminiManualAdapter().run(csv_path=ROOT / "tests" / "fixtures" / "gemini_sample.csv")
    db.upsert_events(p.events + g.events)
    for m in p.session_metas:
        db.upsert_session_meta(m)
    payload = build_dashboard_payload(db)
    assert "perplexity" in payload["totals"]["providers"]
    assert "gemini" in payload["totals"]["providers"]
    assert payload["totals"]["cost_by_rail"]["subscription"] == 20.0
    assert payload["totals"]["cost_by_product"]["perplexity"] == 20.0
    db.close()


def test_get_adapter_codex():
    a = get_adapter("codex-jsonl")
    assert a.product == "codex"
