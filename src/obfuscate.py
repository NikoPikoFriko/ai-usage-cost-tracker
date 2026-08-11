"""
Funny translator / dataset anonymizer.

Same schema + analytics shape (tokens, costs, models, rails, timestamps).
Private free-text and identifiers → absurd, non-reversible placeholders.
Not encryption — hard anonymization with a comic voice.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

# --- comic lexicons (public-safe silly nouns) ---

ADJECTIVES = [
    "cosmic",
    "pickle",
    "velvet",
    "quantum",
    "soggy",
    "neon",
    "lunar",
    "spicy",
    "bamboo",
    "turbo",
    "haunted",
    "butter",
    "crystal",
    "wobbly",
    "electric",
    "mossy",
    "chrome",
    "banana",
    "silent",
    "fizzy",
    "marble",
    "roaring",
    "tiny",
    "giant",
    "sleepy",
    "sparkly",
    "rusty",
    "golden",
    "foggy",
    "zesty",
]

NOUNS = [
    "badger",
    "toaster",
    "comet",
    "waffle",
    "penguin",
    "cactus",
    "noodle",
    "spaceship",
    "llama",
    "teapot",
    "mushroom",
    "trombone",
    "raccoon",
    "volcano",
    "biscuit",
    "octopus",
    "lantern",
    "squirrel",
    "zeppelin",
    "pretzel",
    "dragon",
    "kumquat",
    "harbor",
    "meadow",
    "circuit",
    "balloon",
    "glacier",
    "banjo",
    "meteor",
    "sandwich",
]

PATH_SEGMENTS = [
    "forest",
    "basement",
    "attic",
    "harbor",
    "lab",
    "kitchen",
    "orbit",
    "swamp",
    "castle",
    "garage",
    "reef",
    "plaza",
    "tunnel",
    "meadow",
    "station",
    "dock",
]

# Fields that carry identity / free text (rewrite)
PRIVATE_STRING_KEYS = {
    "label",
    "notes",
    "title",
    "raw_ref",
    "cwd",
    "originator",
    "prompt_text_hash",
    "billing_identity",  # may leak plan naming — map to generic
}

# Keep as-is for analytics (unless empty)
PRESERVE_KEYS = {
    "source_product",
    "channel",
    "grain",
    "money_rail",
    "model",
    "role",
    "service_tier",
    "evidence_class",
    "grade",
    "ingest_channel",
    "coverage",
    "gap_code",
    "input_tokens",
    "output_tokens",
    "tokens_in",
    "tokens_out",
    "tokens_cached",
    "cached_input_tokens",
    "reasoning_tokens",
    "cache_write_input_tokens",
    "total_tokens",
    "cost_usd",
    "unit_price_in_per_1m",
    "unit_price_out_per_1m",
    "unit_price_cached_in_per_1m",
    "pricing_as_of",
    "events_n",
    "tokens_total",
}

# IDs: remap consistently, not leave real UUIDs
ID_KEYS = {"event_id", "session_id", "parent_event_id", "id"}

# Timestamps: optional shift (default: keep relative shape, shift epoch)
TS_KEYS = {"ts_utc", "ts", "started_at", "ended_at", "finished_at"}


def _digest(s: str, salt: str) -> int:
    h = hashlib.sha256(f"{salt}|{s}".encode("utf-8")).hexdigest()
    return int(h[:12], 16)


def funny_phrase(seed: str, salt: str, *, kind: str = "thing") -> str:
    n = _digest(seed, salt + kind)
    adj = ADJECTIVES[n % len(ADJECTIVES)]
    noun = NOUNS[(n // 7) % len(NOUNS)]
    if kind == "path":
        a = PATH_SEGMENTS[n % len(PATH_SEGMENTS)]
        b = PATH_SEGMENTS[(n // 11) % len(PATH_SEGMENTS)]
        c = NOUNS[(n // 13) % len(NOUNS)]
        return f"lab/{a}/{b}/{adj}-{c}"
    if kind == "session":
        return f"ses_{adj}_{noun}_{(n % 9000) + 1000}"
    if kind == "event":
        return f"ev_{adj[:3]}{noun[:3]}_{n % 10**8:08x}"
    if kind == "label":
        verbs = ["refactor", "summon", "debug", "polish", "yeet", "nibble", "launch"]
        v = verbs[n % len(verbs)]
        return f"{v}-{adj}-{noun}"
    if kind == "billing":
        return f"plan-{adj}-tier"
    if kind == "hash":
        return hashlib.sha256(f"obf|{salt}|{seed}".encode()).hexdigest()[:32]
    return f"{adj}-{noun}"


@dataclass
class ObfuscationMap:
    """In-memory map for one run (not saved — not reversible by design if discarded)."""

    salt: str
    id_map: dict[str, str] = field(default_factory=dict)
    string_map: dict[str, str] = field(default_factory=dict)
    ts_shift_seconds: int = 0

    def map_id(self, value: str, *, kind: str = "event") -> str:
        if not value:
            return value
        if value not in self.id_map:
            self.id_map[value] = funny_phrase(value, self.salt, kind=kind)
        return self.id_map[value]

    def map_string(self, value: str, *, kind: str = "thing") -> str:
        if value is None:
            return value
        if not isinstance(value, str):
            return value
        if value == "":
            return value
        key = f"{kind}:{value}"
        if key not in self.string_map:
            # Paths / windows paths → funny path
            if kind == "path" or re.search(r"[\\/]", value) or re.match(r"^[A-Za-z]:\\", value):
                self.string_map[key] = funny_phrase(value, self.salt, kind="path")
            elif kind == "label":
                self.string_map[key] = funny_phrase(value, self.salt, kind="label")
            elif kind == "billing":
                self.string_map[key] = funny_phrase(value, self.salt, kind="billing")
            elif kind == "hash":
                self.string_map[key] = funny_phrase(value, self.salt, kind="hash")
            else:
                self.string_map[key] = funny_phrase(value, self.salt, kind="thing")
        return self.string_map[key]


def _parse_ts(value: str) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    v = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        try:
            return datetime.fromisoformat(v[:19]).replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def _format_ts(dt: datetime, original: str) -> str:
    if original.endswith("Z") or "+00:00" in original or original.endswith("+00:00"):
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    # keep offset-ish
    return dt.isoformat()


def shift_timestamp(value: str, shift_seconds: int) -> str:
    dt = _parse_ts(value)
    if dt is None:
        return funny_phrase(value, "ts", kind="thing")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return _format_ts(dt + timedelta(seconds=shift_seconds), value)


def obfuscate_value(
    key: str,
    value: Any,
    om: ObfuscationMap,
    *,
    parent_key: str = "",
) -> Any:
    if value is None:
        return None

    if key in ID_KEYS and isinstance(value, str):
        kind = "session" if "session" in key else "event"
        return om.map_id(value, kind=kind)

    if key in TS_KEYS and isinstance(value, str):
        if om.ts_shift_seconds:
            return shift_timestamp(value, om.ts_shift_seconds)
        return value  # relative shape preserved without shift

    if key in PRESERVE_KEYS:
        return value

    if key in PRIVATE_STRING_KEYS and isinstance(value, str):
        if key in ("raw_ref", "cwd"):
            return om.map_string(value, kind="path")
        if key == "label":
            return om.map_string(value, kind="label")
        if key == "billing_identity":
            return om.map_string(value, kind="billing")
        if key == "prompt_text_hash":
            return om.map_string(value, kind="hash")
        if key in ("title", "notes", "originator"):
            return om.map_string(value, kind="thing")
        return om.map_string(value, kind="thing")

    if isinstance(value, dict):
        return obfuscate_obj(value, om)
    if isinstance(value, list):
        return [obfuscate_value(key, v, om) for v in value]

    # Unknown string fields that look private
    if isinstance(value, str) and key not in PRESERVE_KEYS:
        if re.search(r"[\\/]", value) or re.match(r"^[A-Za-z]:\\", value):
            return om.map_string(value, kind="path")
        if len(value) > 40 and " " in value:
            return om.map_string(value, kind="thing")
    return value


def obfuscate_obj(obj: dict[str, Any], om: ObfuscationMap) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in obj.items():
        out[k] = obfuscate_value(k, v, om)
    return out


def obfuscate_events(
    events: Iterable[dict[str, Any]],
    *,
    salt: str,
    shift_days: int = 0,
) -> tuple[list[dict[str, Any]], ObfuscationMap]:
    om = ObfuscationMap(salt=salt, ts_shift_seconds=shift_days * 86400)
    return [obfuscate_obj(dict(e), om) for e in events], om


def obfuscate_dashboard_payload(
    payload: dict[str, Any],
    *,
    salt: str,
    shift_days: int = 0,
) -> dict[str, Any]:
    """Obfuscate full web/data.json shaped payload."""
    om = ObfuscationMap(salt=salt, ts_shift_seconds=shift_days * 86400)
    out = deepcopy(payload)
    if "events" in out and isinstance(out["events"], list):
        out["events"] = [obfuscate_obj(dict(e), om) for e in out["events"]]
    if "sessions" in out and isinstance(out["sessions"], list):
        out["sessions"] = [obfuscate_obj(dict(s), om) for s in out["sessions"]]
    # totals / meta: scrub notes that might mention private stuff
    if "meta" in out and isinstance(out["meta"], dict):
        meta = dict(out["meta"])
        meta["data_class"] = "FUNNY_PUBLIC"
        meta["obfuscated"] = True
        meta["obfuscation"] = (
            "private strings remapped to comic placeholders; ids remapped; "
            "tokens/costs/models/rails preserved"
        )
        meta["note"] = (
            "Synthetic public pack — not real projects. "
            "Analytics shape preserved; private fields are jokes."
        )
        meta.pop("generated_at", None)
        meta["generated_at"] = datetime.now(timezone.utc).isoformat()
        out["meta"] = meta
    if "gaps" in out and isinstance(out["gaps"], list):
        for g in out["gaps"]:
            if isinstance(g, dict) and g.get("example_event_id"):
                g["example_event_id"] = om.map_id(str(g["example_event_id"]), kind="event")
    return out


def write_funny_pack(
    payload: dict[str, Any],
    out_dir: Path,
    *,
    salt: str,
    shift_days: int = 0,
    name: str = "funny_pack",
) -> dict[str, Path]:
    """
    Write shareable pack:
      out_dir/name/data.json
      out_dir/name/events.jsonl
      out_dir/name/README.md
    """
    out_dir = Path(out_dir)
    pack = out_dir / name
    pack.mkdir(parents=True, exist_ok=True)

    funny = obfuscate_dashboard_payload(payload, salt=salt, shift_days=shift_days)
    data_path = pack / "data.json"
    data_path.write_text(json.dumps(funny, indent=2), encoding="utf-8")

    events_path = pack / "events.jsonl"
    with events_path.open("w", encoding="utf-8") as f:
        for e in funny.get("events") or []:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    readme = pack / "README.md"
    n_ev = len(funny.get("events") or [])
    n_se = len(funny.get("sessions") or [])
    totals = funny.get("totals") or {}
    readme.write_text(
        f"""# Funny public pack — `{name}`

**Same shape, same analytics value — private fields hilariously obfuscated.**

| | |
|--|--|
| Events | {n_ev} |
| Sessions | {n_se} |
| Providers | {totals.get("providers")} |
| Cost by rail | {totals.get("cost_by_rail")} |
| Data class | FUNNY_PUBLIC |

## Preserved (useful)

- tokens in/out/cached  
- cost_usd  
- model ids  
- source_product / money_rail / grain  
- relative structure of sessions & events  
- timestamps{(" (shifted by " + str(shift_days) + " days)") if shift_days else " (original calendar left; ids/names scrubbed)"}

## Scrubbed (jokes)

- session titles, labels, notes  
- file paths / raw_ref / cwd  
- real session/event ids  
- billing identity strings  
- any free text that looked private  

## Not cryptography

Placeholders are **one-way comic maps** for a single export run.  
Do not treat this as secure encryption of the original data — treat originals as private and this pack as public-safe.

## Use

```bash
# point UI at this pack (copy data.json to web/ or serve directory)
python -m src.cli serve
# or open tests against events.jsonl
```

Generated by `python -m src.cli funny-export`.
""",
        encoding="utf-8",
    )

    return {"dir": pack, "data_json": data_path, "events_jsonl": events_path, "readme": readme}


def load_payload_from_db(db_path: Path) -> dict[str, Any]:
    from src.export_web import build_dashboard_payload
    from src.db import TrackerDB

    db = TrackerDB(db_path)
    try:
        return build_dashboard_payload(db)
    finally:
        db.close()


def load_payload_from_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
