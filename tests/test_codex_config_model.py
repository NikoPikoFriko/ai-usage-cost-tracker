from pathlib import Path

from src.adapters.codex_jsonl import parse_rollout_file, read_codex_default_model
from src.cost import load_pricing

ROOT = Path(__file__).resolve().parents[1]
PRICING = ROOT / "config" / "PRICING_MODELS.csv"


def test_read_codex_default_model_from_toml(tmp_path: Path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '# test fixture — no secrets\nmodel = "gpt-5.6-terra"\nmodel_provider = "openai"\n',
        encoding="utf-8",
    )
    assert read_codex_default_model(tmp_path) == "gpt-5.6-terra"


def test_read_codex_default_model_ignores_non_model(tmp_path: Path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('api_key = "sk-not-a-model"\nfoo = "bar"\n', encoding="utf-8")
    assert read_codex_default_model(tmp_path) is None


def test_parse_uses_default_model_when_no_discovery(tmp_path: Path):
    """JSONL without model lines uses default_model for turns."""
    p = tmp_path / "rollout-no-model.jsonl"
    lines = [
        '{"timestamp":"2026-08-10T12:00:00Z","type":"session_meta","payload":{"id":"ses-nm","session_id":"ses-nm","cwd":"/tmp/x"}}',
        '{"timestamp":"2026-08-10T12:00:01Z","type":"event_msg","payload":{"type":"token_count","info":{"last_token_usage":{"input_tokens":10,"output_tokens":5,"total_tokens":15}},"rate_limits":{"plan_type":"team"}}}',
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rates = load_pricing(PRICING)
    events, meta = parse_rollout_file(p, rates, default_model="gpt-5.6-terra")
    assert len(events) == 1
    assert events[0].model == "gpt-5.6-terra"
    assert meta.get("model_default") == "gpt-5.6-terra"
