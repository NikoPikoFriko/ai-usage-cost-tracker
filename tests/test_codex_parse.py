from pathlib import Path

from src.adapters.codex_jsonl import parse_rollout_file
from src.cost import load_pricing
from src.db import TrackerDB

ROOT = Path(__file__).resolve().parents[1]
PRICING = ROOT / "config" / "PRICING_MODELS.csv"
FIXTURES = ROOT / "tests" / "fixtures"
SAMPLE = FIXTURES / "sample_rollout.jsonl"
LATE = FIXTURES / "late_model_rollout.jsonl"
MULTI = FIXTURES / "multi_model_rollout.jsonl"
ZERO = FIXTURES / "zero_usage_rollout.jsonl"
SUB = FIXTURES / "subagent_surface_rollout.jsonl"


def test_parse_fixture_events():
    rates = load_pricing(PRICING)
    events, meta = parse_rollout_file(SAMPLE, rates)
    assert meta["session_id"] == "ses-test-001"
    assert meta["title"] == "demo-app"
    assert len(events) == 2
    assert events[0].source_product == "codex"
    assert events[0].ingest_channel == "codex_local_session_jsonl"
    assert events[0].input_tokens == 1000
    assert events[0].cached_input_tokens == 200
    assert events[0].model == "gpt-5.6-terra"
    assert events[0].cost_usd is not None and events[0].cost_usd > 0
    assert events[0].grain == "turn"
    assert events[0].money_rail in ("credits", "api_metered")

    events2, _ = parse_rollout_file(SAMPLE, rates)
    assert events[0].event_id == events2[0].event_id


def test_db_upsert_idempotent(tmp_path: Path):
    rates = load_pricing(PRICING)
    events, meta = parse_rollout_file(SAMPLE, rates)
    db_path = tmp_path / "t.db"
    db = TrackerDB(db_path)
    n1 = db.upsert_events(events)
    db.upsert_session_meta(meta)
    n2 = db.upsert_events(events)
    assert n1 == 2 and n2 == 2
    assert db.count_events() == 2
    db.close()


def test_late_model_two_pass_assigns_session_fallback():
    """token_count before first model line gets session last-known model (I1)."""
    assert LATE.is_file()
    rates = load_pricing(PRICING)
    events, meta = parse_rollout_file(LATE, rates)
    assert meta["session_id"] == "ses-late-model"
    assert len(events) == 2
    # First turn has no prior model → session last-known (later discovery)
    assert events[0].model == "gpt-5.6-terra"
    assert events[1].model == "gpt-5.6-terra"
    assert events[0].cost_usd is not None


def test_multi_model_fixture():
    rates = load_pricing(PRICING)
    events, meta = parse_rollout_file(MULTI, rates)
    assert meta["session_id"] == "ses-multi-model"
    assert len(events) == 2
    assert events[0].model == "gpt-5.6-terra"
    assert events[1].model == "gpt-5.4-mini"


def test_zero_usage_skipped():
    rates = load_pricing(PRICING)
    events, meta = parse_rollout_file(ZERO, rates)
    assert meta["session_id"] == "ses-zero"
    assert len(events) == 1
    assert events[0].input_tokens == 300


def test_subagent_surface_marker():
    rates = load_pricing(PRICING)
    events, meta = parse_rollout_file(SUB, rates)
    assert meta["session_id"] == "ses-subagent"
    assert meta.get("source_surface") == "subagent" or (
        events and events[0].source_surface == "subagent"
    )
    assert len(events) == 1
