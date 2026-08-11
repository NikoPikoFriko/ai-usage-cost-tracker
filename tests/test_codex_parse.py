import json
from pathlib import Path

from src.adapters.codex_jsonl import parse_rollout_file
from src.cost import load_pricing
from src.db import TrackerDB

ROOT = Path(__file__).resolve().parents[1]
PRICING = ROOT / "config" / "PRICING_MODELS.csv"
FIXTURE = ROOT / "tests" / "fixtures" / "sample_rollout.jsonl"


def _write_fixture() -> None:
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        {
            "timestamp": "2026-08-10T12:00:00.000Z",
            "type": "session_meta",
            "payload": {
                "session_id": "ses-test-001",
                "id": "ses-test-001",
                "cwd": "D:/Projects/active/demo-app",
                "originator": "codex_work_desktop",
                "source": "vscode",
                "model_provider": "openai",
                "timestamp": "2026-08-10T12:00:00.000Z",
            },
        },
        {
            "timestamp": "2026-08-10T12:00:00.500Z",
            "type": "response_item",
            "payload": {"type": "message", "model": "gpt-5.6-terra"},
        },
        {
            "timestamp": "2026-08-10T12:00:01.000Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 1000,
                        "cached_input_tokens": 200,
                        "cache_write_input_tokens": 0,
                        "output_tokens": 100,
                        "reasoning_output_tokens": 40,
                        "total_tokens": 1100,
                    },
                    "total_token_usage": {
                        "input_tokens": 1000,
                        "cached_input_tokens": 200,
                        "output_tokens": 100,
                        "total_tokens": 1100,
                    },
                },
                "rate_limits": {"plan_type": "team"},
            },
        },
        {
            "timestamp": "2026-08-10T12:01:00.000Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 2000,
                        "cached_input_tokens": 1000,
                        "cache_write_input_tokens": 0,
                        "output_tokens": 200,
                        "reasoning_output_tokens": 50,
                        "total_tokens": 2200,
                    }
                },
                "rate_limits": {"plan_type": "team"},
            },
        },
    ]
    FIXTURE.write_text(
        "\n".join(json.dumps(x) for x in lines) + "\n",
        encoding="utf-8",
    )


def test_parse_fixture_events():
    _write_fixture()
    rates = load_pricing(PRICING)
    events, meta = parse_rollout_file(FIXTURE, rates)
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

    # idempotent ids stable
    events2, _ = parse_rollout_file(FIXTURE, rates)
    assert events[0].event_id == events2[0].event_id


def test_db_upsert_idempotent(tmp_path: Path):
    _write_fixture()
    rates = load_pricing(PRICING)
    events, meta = parse_rollout_file(FIXTURE, rates)
    db_path = tmp_path / "t.db"
    db = TrackerDB(db_path)
    n1 = db.upsert_events(events)
    db.upsert_session_meta(meta)
    n2 = db.upsert_events(events)
    assert n1 == 2 and n2 == 2
    assert db.count_events() == 2
    db.close()
