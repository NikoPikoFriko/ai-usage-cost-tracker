from pathlib import Path

from src.adapters.codex_jsonl import parse_rollout_file
from src.cost import load_pricing

ROOT = Path(__file__).resolve().parents[1]
PRICING = ROOT / "config" / "PRICING_MODELS.csv"
FIXTURE = ROOT / "tests" / "fixtures" / "service_tier_rollout.jsonl"


def test_service_tier_captured_when_present():
    rates = load_pricing(PRICING)
    events, meta = parse_rollout_file(FIXTURE, rates)
    assert meta["session_id"] == "ses-tier"
    assert len(events) == 1
    assert events[0].service_tier == "default"


def test_service_tier_absent_is_none():
    rates = load_pricing(PRICING)
    sample = ROOT / "tests" / "fixtures" / "sample_rollout.jsonl"
    events, _ = parse_rollout_file(sample, rates)
    assert events
    assert events[0].service_tier is None
