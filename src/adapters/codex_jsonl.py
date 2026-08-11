"""Parse Codex local session JSONL (rollout-*.jsonl) into UsageEvents."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterator, Optional

from src.cost import load_pricing, price_event_fields
from src.models import UsageEvent

CHANNEL_ID = "codex_local_session_jsonl"


def default_codex_home() -> Path:
    env = os.environ.get("CODEX_HOME")
    if env:
        return Path(env)
    return Path.home() / ".codex"


def iter_rollout_files(codex_home: Path, include_archived: bool = True) -> list[Path]:
    files: list[Path] = []
    sessions = codex_home / "sessions"
    if sessions.is_dir():
        files.extend(sessions.rglob("rollout-*.jsonl"))
    if include_archived:
        archived = codex_home / "archived_sessions"
        if archived.is_dir():
            files.extend(archived.rglob("*.jsonl"))
    # stable order
    return sorted(set(files), key=lambda p: str(p).lower())


def _stable_event_id(
    channel: str,
    session_id: str,
    ts_utc: str,
    turn_index: int,
    last: dict[str, Any],
) -> str:
    payload = "|".join(
        [
            channel,
            session_id,
            ts_utc,
            str(turn_index),
            str(last.get("input_tokens")),
            str(last.get("output_tokens")),
            str(last.get("cached_input_tokens")),
            str(last.get("total_tokens")),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _short_title(cwd: Optional[str], session_id: str) -> str:
    if cwd:
        try:
            return Path(cwd).name or session_id[:12]
        except Exception:
            pass
    return session_id[:12]


def _surface_from_meta(originator: Optional[str], source: Any) -> str:
    if originator:
        o = str(originator).lower()
        if "desktop" in o:
            return "windows_app"
        if "cli" in o:
            return "cli"
    if isinstance(source, str) and source.lower() in {"vscode", "cli", "app"}:
        return "vscode" if source.lower() == "vscode" else source.lower()
    if isinstance(source, dict) and "subagent" in source:
        return "subagent"
    return "cli"


def _looks_like_model(s: str) -> bool:
    s = s.strip()
    if not s or len(s) > 80:
        return False
    low = s.lower()
    return (
        low.startswith("gpt-")
        or low.startswith("o1")
        or low.startswith("o3")
        or low.startswith("o4")
        or low.startswith("codex")
        or "codex" in low
        or low.startswith("chat-")
    )


def _extract_model(obj: dict[str, Any], fallback: str) -> str:
    """Best-effort model discovery — shallow keys only (never retain prompt text)."""
    for key in ("model", "model_slug", "active_model"):
        v = obj.get(key)
        if isinstance(v, str) and _looks_like_model(v):
            return v.strip()
    pl = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
    for key in ("model", "model_slug", "active_model"):
        v = pl.get(key)
        if isinstance(v, str) and _looks_like_model(v):
            return v.strip()
    info = pl.get("info") if isinstance(pl.get("info"), dict) else None
    if info:
        for key in ("model", "model_slug"):
            v = info.get(key)
            if isinstance(v, str) and _looks_like_model(v):
                return v.strip()
    # turn / response envelopes often nest once more
    for nest_key in ("turn", "response", "message", "item"):
        nest = pl.get(nest_key)
        if isinstance(nest, dict):
            for key in ("model", "model_slug"):
                v = nest.get(key)
                if isinstance(v, str) and _looks_like_model(v):
                    return v.strip()
    return fallback


def parse_rollout_file(
    path: Path,
    rates: list,
    default_model: str = "unknown",
) -> tuple[list[UsageEvent], dict[str, Any]]:
    """Return (events, session_meta_row)."""
    session_id = path.stem  # fallback
    model = default_model
    cwd = None
    originator = None
    source = None
    started_at = None
    surface = "cli"
    events: list[UsageEvent] = []
    turn_index = 0
    models_seen: set[str] = set()

    try:
        fh = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return [], {}

    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            # fast reject: only parse lines that might matter
            if (
                '"session_meta"' not in line
                and '"token_count"' not in line
                and '"model"' not in line
            ):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            # opportunistic model scan (no text retention)
            m = _extract_model(obj, "")
            if m:
                model = m
                models_seen.add(m)

            t = obj.get("type")
            pl = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
            ts = obj.get("timestamp") or ""

            if t == "session_meta":
                sid = pl.get("id") or pl.get("session_id")
                if isinstance(sid, str) and sid:
                    session_id = sid
                if pl.get("cwd"):
                    cwd = pl.get("cwd")
                originator = pl.get("originator") or originator
                source = pl.get("source") if pl.get("source") is not None else source
                if not started_at:
                    started_at = pl.get("timestamp") or ts
                surface = _surface_from_meta(
                    originator if isinstance(originator, str) else None,
                    source,
                )
                continue

            if t == "event_msg" and pl.get("type") == "token_count":
                info = pl.get("info") if isinstance(pl.get("info"), dict) else {}
                last = (
                    info.get("last_token_usage")
                    if isinstance(info.get("last_token_usage"), dict)
                    else {}
                )
                if not last:
                    last = (
                        info.get("total_token_usage")
                        if isinstance(info.get("total_token_usage"), dict)
                        else {}
                    )
                if not last:
                    continue

                inp = int(last.get("input_tokens") or 0)
                out = int(last.get("output_tokens") or 0)
                cached = int(last.get("cached_input_tokens") or 0)
                reasoning = int(last.get("reasoning_output_tokens") or 0)
                cache_write = int(last.get("cache_write_input_tokens") or 0)
                total = int(last.get("total_tokens") or (inp + out))

                if inp == 0 and out == 0 and total == 0:
                    continue

                turn_index += 1
                event_model = model or default_model
                priced = price_event_fields(
                    rates,
                    model=event_model,
                    ts_utc=ts,
                    input_tokens=inp,
                    output_tokens=out,
                    cached_input_tokens=cached,
                    cache_write_input_tokens=cache_write,
                )

                rl = pl.get("rate_limits") if isinstance(pl.get("rate_limits"), dict) else {}
                plan = rl.get("plan_type")
                billing = "chatgpt_credits" if plan else "unknown"

                grade = "OBS" if priced["priced"] else "GAP"
                if priced["priced"] and priced.get("rate_evidence") == "CAND":
                    grade = "CAND"

                eid = _stable_event_id(CHANNEL_ID, session_id, ts, turn_index, last)
                label = f"turn-{turn_index}"

                events.append(
                    UsageEvent(
                        event_id=eid,
                        source_product="codex",
                        source_surface=surface,
                        session_id=session_id,
                        ts_utc=ts or started_at or "",
                        model=event_model,
                        input_tokens=inp,
                        output_tokens=out,
                        cached_input_tokens=cached,
                        reasoning_tokens=reasoning,
                        cache_write_input_tokens=cache_write,
                        total_tokens=total,
                        unit_price_in_per_1m=priced["unit_price_in_per_1m"],
                        unit_price_out_per_1m=priced["unit_price_out_per_1m"],
                        unit_price_cached_in_per_1m=priced["unit_price_cached_in_per_1m"],
                        cost_usd=priced["cost_usd"],
                        pricing_as_of=priced["pricing_as_of"],
                        billing_identity=billing,
                        evidence_class=grade,
                        ingest_channel=CHANNEL_ID,
                        raw_ref=str(path),
                        notes=None,
                        label=label,
                    )
                )

    meta = {
        "session_id": session_id,
        "title": _short_title(cwd if isinstance(cwd, str) else None, session_id),
        "source_product": "codex",
        "source_surface": surface,
        "cwd": cwd if isinstance(cwd, str) else None,
        "started_at": started_at,
        "model_default": model,
        "originator": originator if isinstance(originator, str) else None,
    }
    return events, meta


def ingest_codex_jsonl(
    codex_home: Optional[Path] = None,
    pricing_csv: Optional[Path] = None,
    include_archived: bool = True,
    max_files: Optional[int] = None,
) -> tuple[list[UsageEvent], list[dict[str, Any]], dict[str, int]]:
    """
    Walk Codex home, parse rollouts, return events, session metas, stats.
    """
    home = codex_home or default_codex_home()
    if pricing_csv is None:
        pricing_csv = Path(__file__).resolve().parents[2] / "config" / "PRICING_MODELS.csv"
    rates = load_pricing(pricing_csv)
    files = iter_rollout_files(home, include_archived=include_archived)
    if max_files is not None:
        files = files[: max(0, max_files)]

    all_events: list[UsageEvent] = []
    metas: list[dict[str, Any]] = []
    skipped = 0
    for f in files:
        try:
            evs, meta = parse_rollout_file(f, rates)
        except Exception:
            skipped += 1
            continue
        if meta.get("session_id"):
            metas.append(meta)
        all_events.extend(evs)

    stats = {
        "files_seen": len(files),
        "events": len(all_events),
        "files_error": skipped,
        "codex_home": str(home),
    }
    return all_events, metas, stats
