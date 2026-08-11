"""Usage event dataclasses (FC-2026-08-10-AI-USAGE-COST)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class UsageEvent:
    event_id: str
    source_product: str  # chatgpt | codex
    session_id: str
    ts_utc: str
    model: str
    input_tokens: int
    output_tokens: int
    evidence_class: str
    ingest_channel: str
    source_surface: Optional[str] = None
    parent_event_id: Optional[str] = None
    prompt_text_hash: Optional[str] = None
    cached_input_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    cache_write_input_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    unit_price_in_per_1m: Optional[float] = None
    unit_price_out_per_1m: Optional[float] = None
    unit_price_cached_in_per_1m: Optional[float] = None
    cost_usd: Optional[float] = None
    pricing_as_of: Optional[str] = None
    billing_identity: Optional[str] = None
    service_tier: Optional[str] = None
    raw_ref: Optional[str] = None
    notes: Optional[str] = None
    label: Optional[str] = None  # UI-only short label (not full prompt)

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SessionRollup:
    session_id: str
    source_product: str
    title: str
    started_at: Optional[str]
    events_n: int
    tokens_in: int
    tokens_out: int
    tokens_cached: int
    cost_usd: Optional[float]
    model_mix: list[str] = field(default_factory=list)
    grade: str = "CAND"
    coverage: str = "0/0"
    source_surface: Optional[str] = None
