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


def test_same_record_model_not_overwritten_by_later_discovery(tmp_path: Path):
    """token_count envelope model must win over a later different discovery (I1)."""
    p = tmp_path / "rollout-same-record-model.jsonl"
    p.write_text(
        "\n".join(
            [
                '{"timestamp":"2026-08-10T12:00:00Z","type":"session_meta","payload":{"id":"ses-srm","session_id":"ses-srm","cwd":"/tmp/srm"}}',
                '{"timestamp":"2026-08-10T12:00:01Z","type":"event_msg","model":"gpt-5.6-terra","payload":{"type":"token_count","info":{"model":"gpt-5.6-terra","last_token_usage":{"input_tokens":1000000,"output_tokens":0,"total_tokens":1000000}},"rate_limits":{"plan_type":"team"}}}',
                '{"timestamp":"2026-08-10T12:00:02Z","type":"response_item","payload":{"type":"message","model":"gpt-5.4-mini"}}',
                '{"timestamp":"2026-08-10T12:00:03Z","type":"event_msg","payload":{"type":"token_count","info":{"last_token_usage":{"input_tokens":10,"output_tokens":0,"total_tokens":10}},"rate_limits":{"plan_type":"team"}}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    rates = load_pricing(PRICING)
    events, meta = parse_rollout_file(p, rates)
    assert meta["session_id"] == "ses-srm"
    assert len(events) == 2
    assert events[0].model == "gpt-5.6-terra"
    assert events[1].model == "gpt-5.4-mini"
    # 1M uncached terra input @ $2/1M — must not be priced as mini @ $0.75
    assert events[0].cost_usd is not None
    assert abs(events[0].cost_usd - 2.0) < 1e-6


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
