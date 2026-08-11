from pathlib import Path

from src.obfuscate import (
    obfuscate_dashboard_payload,
    obfuscate_events,
    write_funny_pack,
)


def _sample_payload():
    return {
        "meta": {
            "data_class": "LIVE",
            "note": "real private note about D:\\Secret\\Project",
            "generated_at": "2026-08-10T12:00:00Z",
        },
        "totals": {
            "cost_usd_priced": 1.5,
            "cost_by_rail": {"credits": 1.5},
            "providers": ["codex"],
            "events_n": 2,
            "sessions_n": 1,
        },
        "sessions": [
            {
                "session_id": "019fef38-real-uuid-here",
                "channel": "codex",
                "title": "STATION_DISK_LAW real room",
                "started_at": "2026-08-10T09:00:00Z",
                "events_n": 2,
                "tokens_in": 1000,
                "tokens_out": 200,
                "cost_usd": 1.5,
                "model_mix": ["gpt-5.6-terra"],
                "grade": "OBS",
                "coverage": "2/2",
                "money_rails": ["credits"],
            }
        ],
        "events": [
            {
                "event_id": "deadbeefcafebabe01",
                "session_id": "019fef38-real-uuid-here",
                "channel": "codex",
                "ts": "2026-08-10T09:01:00Z",
                "label": "fix-auth-for-niko",
                "role": "cli",
                "model": "gpt-5.6-terra",
                "grain": "turn",
                "money_rail": "credits",
                "tokens_in": 500,
                "tokens_out": 100,
                "tokens_cached": 50,
                "cost_usd": 0.5,
                "grade": "OBS",
                "raw_ref": r"C:\Users\NIKO\.codex\sessions\secret\rollout.jsonl",
                "billing_identity": "chatgpt_credits",
            },
            {
                "event_id": "deadbeefcafebabe02",
                "session_id": "019fef38-real-uuid-here",
                "channel": "codex",
                "ts": "2026-08-10T09:02:00Z",
                "label": "turn-2",
                "role": "cli",
                "model": "gpt-5.6-terra",
                "grain": "turn",
                "money_rail": "credits",
                "tokens_in": 500,
                "tokens_out": 100,
                "tokens_cached": 0,
                "cost_usd": 1.0,
                "grade": "OBS",
                "raw_ref": r"C:\Users\NIKO\.codex\sessions\secret\rollout.jsonl",
            },
        ],
        "gaps": [],
    }


def test_preserves_analytics_shape():
    src = _sample_payload()
    out = obfuscate_dashboard_payload(src, salt="test-salt", shift_days=0)
    assert out["meta"]["data_class"] == "FUNNY_PUBLIC"
    assert out["meta"]["obfuscated"] is True
    assert len(out["events"]) == 2
    e0, e1 = out["events"]
    assert e0["tokens_in"] == 500
    assert e0["cost_usd"] == 0.5
    assert e0["model"] == "gpt-5.6-terra"
    assert e0["money_rail"] == "credits"
    assert e0["grain"] == "turn"
    assert e0["channel"] == "codex"
    # private scrubbed
    assert e0["session_id"] != "019fef38-real-uuid-here"
    assert "NIKO" not in e0["raw_ref"]
    assert "fix-auth-for-niko" not in e0["label"]
    assert "Users" not in e0["raw_ref"]
    # stable mapping within run
    assert e0["session_id"] == e1["session_id"]
    assert out["sessions"][0]["session_id"] == e0["session_id"]
    assert out["sessions"][0]["title"] != "STATION_DISK_LAW real room"
    assert out["sessions"][0]["cost_usd"] == 1.5


def test_shift_days_moves_calendar():
    src = _sample_payload()
    out = obfuscate_dashboard_payload(src, salt="s", shift_days=30)
    assert out["events"][0]["ts"].startswith("2026-09-")


def test_write_funny_pack(tmp_path: Path):
    paths = write_funny_pack(
        _sample_payload(),
        tmp_path,
        salt="pack-salt",
        shift_days=0,
        name="demo",
    )
    assert paths["data_json"].is_file()
    assert paths["events_jsonl"].is_file()
    assert paths["readme"].is_file()
    text = paths["events_jsonl"].read_text(encoding="utf-8")
    assert "NIKO" not in text
    assert "gpt-5.6-terra" in text


def test_same_salt_same_ids():
    ev = [
        {
            "event_id": "abc",
            "session_id": "ses-1",
            "label": "secret",
            "tokens_in": 1,
            "cost_usd": 0.1,
            "model": "x",
            "channel": "codex",
            "money_rail": "credits",
            "grain": "turn",
        }
    ]
    a, _ = obfuscate_events(ev, salt="fixed")
    b, _ = obfuscate_events(ev, salt="fixed")
    assert a[0]["event_id"] == b[0]["event_id"]
    assert a[0]["label"] == b[0]["label"]
