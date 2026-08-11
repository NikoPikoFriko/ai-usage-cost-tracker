"""Provider adapter protocol (multi-provider spend plane)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from src.models import UsageEvent


@dataclass
class IngestResult:
    events: list[UsageEvent]
    session_metas: list[dict[str, Any]]
    stats: dict[str, Any]


@runtime_checkable
class ProviderAdapter(Protocol):
    """One product surface → UsageEvent rows."""

    id: str
    product: str
    description: str

    def run(self, **kwargs: Any) -> IngestResult:
        """Parse local sources; never upload; never read secrets stores."""
        ...


def stable_hash(*parts: str) -> str:
    import hashlib

    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_pricing_csv() -> Path:
    return repo_root() / "config" / "PRICING_MODELS.csv"
