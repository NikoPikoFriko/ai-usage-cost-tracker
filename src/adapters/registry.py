"""Adapter registry — list and resolve ingest channels."""

from __future__ import annotations

from typing import Any, Callable

from src.adapters.base import ProviderAdapter

_LOADERS: dict[str, Callable[[], ProviderAdapter]] = {}
_INITIALIZED = False


def _ensure_builtins() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return
    _INITIALIZED = True

    def codex() -> ProviderAdapter:
        from src.adapters.codex_jsonl import CodexJsonlAdapter

        return CodexJsonlAdapter()

    _LOADERS["codex-jsonl"] = codex

    try:
        from src.adapters.perplexity_manual import PerplexityManualAdapter

        def perplexity() -> ProviderAdapter:
            return PerplexityManualAdapter()

        _LOADERS["perplexity-manual"] = perplexity
    except ImportError:
        pass

    try:
        from src.adapters.gemini_manual import GeminiManualAdapter

        def gemini() -> ProviderAdapter:
            return GeminiManualAdapter()

        _LOADERS["gemini-manual"] = gemini
    except ImportError:
        pass


def list_adapters() -> list[dict[str, str]]:
    _ensure_builtins()
    out = []
    for key, loader in sorted(_LOADERS.items()):
        a = loader()
        out.append(
            {
                "cli_id": key,
                "channel_id": a.id,
                "product": a.product,
                "description": a.description,
            }
        )
    return out


def get_adapter(cli_id: str) -> ProviderAdapter:
    _ensure_builtins()
    if cli_id not in _LOADERS:
        known = ", ".join(sorted(_LOADERS)) or "(none)"
        raise KeyError(f"Unknown adapter '{cli_id}'. Known: {known}")
    return _LOADERS[cli_id]()


def run_adapter(cli_id: str, **kwargs: Any):
    return get_adapter(cli_id).run(**kwargs)
