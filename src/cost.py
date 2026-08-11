"""Pricing join + metered cost formula."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ModelRate:
    model_id: str
    product_family: str
    input_usd_per_1m: float
    output_usd_per_1m: float
    cached_input_usd_per_1m: Optional[float]
    effective_from: str
    source_url: str
    evidence_class: str
    notes: str = ""


def _parse_date(s: str) -> date:
    s = (s or "").strip()
    if not s:
        return date.min
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return date.min


def load_pricing(csv_path: Path) -> list[ModelRate]:
    rates: list[ModelRate] = []
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cached = row.get("cached_input_usd_per_1m", "").strip()
            rates.append(
                ModelRate(
                    model_id=row["model_id"].strip(),
                    product_family=row.get("product_family", "").strip(),
                    input_usd_per_1m=float(row["input_usd_per_1m"]),
                    output_usd_per_1m=float(row["output_usd_per_1m"]),
                    cached_input_usd_per_1m=float(cached) if cached else None,
                    effective_from=row.get("effective_from", "").strip(),
                    source_url=row.get("source_url", "").strip(),
                    evidence_class=row.get("evidence_class", "OBS").strip() or "OBS",
                    notes=row.get("notes", "") or "",
                )
            )
    return rates


def default_aliases_path(pricing_csv: Optional[Path] = None) -> Path:
    if pricing_csv is not None:
        return pricing_csv.parent / "MODEL_ALIASES.csv"
    return Path(__file__).resolve().parents[1] / "config" / "MODEL_ALIASES.csv"


def load_aliases(csv_path: Optional[Path] = None) -> dict[str, str]:
    """Map alias model_id → canonical rate-card model_id (case-sensitive strip)."""
    path = csv_path or default_aliases_path()
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alias = (row.get("alias") or "").strip()
            canon = (row.get("canonical_model_id") or "").strip()
            if alias and canon:
                out[alias] = canon
    return out


_ALIASES_CACHE: Optional[dict[str, str]] = None


def _aliases() -> dict[str, str]:
    global _ALIASES_CACHE
    if _ALIASES_CACHE is None:
        _ALIASES_CACHE = load_aliases()
    return _ALIASES_CACHE


def clear_alias_cache() -> None:
    """Test helper."""
    global _ALIASES_CACHE
    _ALIASES_CACHE = None


def resolve_rate(
    rates: list[ModelRate],
    model_id: str,
    as_of: Optional[str] = None,
    aliases: Optional[dict[str, str]] = None,
) -> Optional[ModelRate]:
    """Pick latest rate for model with effective_from <= as_of date.

    Exact model_id first; then MODEL_ALIASES.csv canonical map.
    If the rate card only has a newer snapshot (common for research CSV),
    fall back to the latest known rate for that model so historical sessions
    still get API-equivalent $ (label honesty stays on evidence_class).
    """
    if not model_id:
        return None
    mid = model_id.strip()
    as_of_d = _parse_date(as_of or date.today().isoformat())

    def _pick(mid_key: str) -> Optional[ModelRate]:
        same = [r for r in rates if r.model_id == mid_key]
        if not same:
            return None
        candidates = [r for r in same if _parse_date(r.effective_from) <= as_of_d]
        pool = candidates if candidates else same
        pool.sort(key=lambda r: _parse_date(r.effective_from), reverse=True)
        return pool[0]

    hit = _pick(mid)
    if hit is not None:
        return hit

    amap = aliases if aliases is not None else _aliases()
    canon = amap.get(mid)
    if not canon or canon == mid:
        return None
    return _pick(canon.strip())


def resolve_rate_with_meta(
    rates: list[ModelRate],
    model_id: str,
    as_of: Optional[str] = None,
    aliases: Optional[dict[str, str]] = None,
) -> tuple[Optional[ModelRate], bool]:
    """Return (rate, used_alias). used_alias True when join needed alias map."""
    if not model_id:
        return None, False
    mid = model_id.strip()
    as_of_d = _parse_date(as_of or date.today().isoformat())

    def _pick(mid_key: str) -> Optional[ModelRate]:
        same = [r for r in rates if r.model_id == mid_key]
        if not same:
            return None
        candidates = [r for r in same if _parse_date(r.effective_from) <= as_of_d]
        pool = candidates if candidates else same
        pool.sort(key=lambda r: _parse_date(r.effective_from), reverse=True)
        return pool[0]

    hit = _pick(mid)
    if hit is not None:
        return hit, False
    amap = aliases if aliases is not None else _aliases()
    canon = amap.get(mid)
    if not canon or canon == mid:
        return None, False
    return _pick(canon.strip()), True


def compute_cost_usd(
    input_tokens: int,
    output_tokens: int,
    rate: ModelRate,
    cached_input_tokens: Optional[int] = None,
    cache_write_input_tokens: Optional[int] = None,
    cache_write_usd_per_1m: Optional[float] = None,
) -> float:
    """
    cost_usd =
      (input - cached) * R_in / 1e6
    + cached * R_cached / 1e6
    + output * R_out / 1e6
    (+ optional cache writes)

    reasoning tokens are already inside output_tokens — do not add again.
    """
    inp = max(0, int(input_tokens or 0))
    out = max(0, int(output_tokens or 0))
    cached = max(0, int(cached_input_tokens or 0))
    if cached > inp:
        cached = inp
    uncached = inp - cached

    r_in = float(rate.input_usd_per_1m)
    r_out = float(rate.output_usd_per_1m)
    if rate.cached_input_usd_per_1m is None:
        # no cache discount → bill all input at R_in
        cost = (inp * r_in + out * r_out) / 1_000_000.0
    else:
        r_cached = float(rate.cached_input_usd_per_1m)
        cost = (uncached * r_in + cached * r_cached + out * r_out) / 1_000_000.0

    cw = max(0, int(cache_write_input_tokens or 0))
    if cw and cache_write_usd_per_1m is not None:
        cost += cw * float(cache_write_usd_per_1m) / 1_000_000.0
    return round(cost, 8)


def price_event_fields(
    rates: list[ModelRate],
    model: str,
    ts_utc: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: Optional[int] = None,
    cache_write_input_tokens: Optional[int] = None,
    aliases: Optional[dict[str, str]] = None,
) -> dict:
    """Return unit prices + cost_usd + pricing_as_of + grade hints.

    Alias joins are CAND (mapping is inferred) even if the base rate row is OBS.
    """
    as_of = ts_utc[:10] if ts_utc else None
    rate, used_alias = resolve_rate_with_meta(rates, model, as_of=as_of, aliases=aliases)
    if rate is None:
        return {
            "unit_price_in_per_1m": None,
            "unit_price_out_per_1m": None,
            "unit_price_cached_in_per_1m": None,
            "cost_usd": None,
            "pricing_as_of": None,
            "priced": False,
            "rate_evidence": None,
            "used_alias": False,
        }
    cost = compute_cost_usd(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        rate=rate,
        cached_input_tokens=cached_input_tokens,
        cache_write_input_tokens=cache_write_input_tokens,
    )
    evidence = "CAND" if used_alias else rate.evidence_class
    return {
        "unit_price_in_per_1m": rate.input_usd_per_1m,
        "unit_price_out_per_1m": rate.output_usd_per_1m,
        "unit_price_cached_in_per_1m": rate.cached_input_usd_per_1m,
        "cost_usd": cost,
        "pricing_as_of": rate.effective_from,
        "priced": True,
        "rate_evidence": evidence,
        "used_alias": used_alias,
    }


def event_ts_to_date_str(ts_utc: str) -> str:
    if not ts_utc:
        return date.today().isoformat()
    try:
        # handle Z
        t = ts_utc.replace("Z", "+00:00")
        return datetime.fromisoformat(t).date().isoformat()
    except ValueError:
        return ts_utc[:10]
