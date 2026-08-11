from src.adapters.registry import get_adapter, list_adapters

def test_registry_has_codex():
    ids = {a["cli_id"] for a in list_adapters()}
    assert "codex-jsonl" in ids
    a = get_adapter("codex-jsonl")
    assert a.product == "codex"
