"""SQLite store for usage_events."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

from src.models import UsageEvent

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_events (
  event_id TEXT PRIMARY KEY,
  source_product TEXT NOT NULL,
  source_surface TEXT,
  session_id TEXT NOT NULL,
  parent_event_id TEXT,
  ts_utc TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_text_hash TEXT,
  input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  cached_input_tokens INTEGER,
  reasoning_tokens INTEGER,
  cache_write_input_tokens INTEGER,
  total_tokens INTEGER,
  unit_price_in_per_1m REAL,
  unit_price_out_per_1m REAL,
  unit_price_cached_in_per_1m REAL,
  cost_usd REAL,
  pricing_as_of TEXT,
  billing_identity TEXT,
  service_tier TEXT,
  evidence_class TEXT NOT NULL,
  ingest_channel TEXT NOT NULL,
  raw_ref TEXT,
  notes TEXT,
  label TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_session ON usage_events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_ts ON usage_events(ts_utc);
CREATE INDEX IF NOT EXISTS idx_events_product ON usage_events(source_product);

CREATE TABLE IF NOT EXISTS ingest_runs (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  channel TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  files_seen INTEGER DEFAULT 0,
  events_upserted INTEGER DEFAULT 0,
  events_skipped INTEGER DEFAULT 0,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS sessions_meta (
  session_id TEXT PRIMARY KEY,
  title TEXT,
  source_product TEXT,
  source_surface TEXT,
  cwd TEXT,
  started_at TEXT,
  model_default TEXT,
  originator TEXT
);
"""


class TrackerDB:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def upsert_events(self, events: Iterable[UsageEvent]) -> int:
        n = 0
        sql = """
        INSERT INTO usage_events (
          event_id, source_product, source_surface, session_id, parent_event_id,
          ts_utc, model, prompt_text_hash, input_tokens, output_tokens,
          cached_input_tokens, reasoning_tokens, cache_write_input_tokens, total_tokens,
          unit_price_in_per_1m, unit_price_out_per_1m, unit_price_cached_in_per_1m,
          cost_usd, pricing_as_of, billing_identity, service_tier,
          evidence_class, ingest_channel, raw_ref, notes, label
        ) VALUES (
          :event_id, :source_product, :source_surface, :session_id, :parent_event_id,
          :ts_utc, :model, :prompt_text_hash, :input_tokens, :output_tokens,
          :cached_input_tokens, :reasoning_tokens, :cache_write_input_tokens, :total_tokens,
          :unit_price_in_per_1m, :unit_price_out_per_1m, :unit_price_cached_in_per_1m,
          :cost_usd, :pricing_as_of, :billing_identity, :service_tier,
          :evidence_class, :ingest_channel, :raw_ref, :notes, :label
        )
        ON CONFLICT(event_id) DO UPDATE SET
          cost_usd=excluded.cost_usd,
          unit_price_in_per_1m=excluded.unit_price_in_per_1m,
          unit_price_out_per_1m=excluded.unit_price_out_per_1m,
          unit_price_cached_in_per_1m=excluded.unit_price_cached_in_per_1m,
          pricing_as_of=excluded.pricing_as_of,
          evidence_class=excluded.evidence_class,
          model=excluded.model,
          label=excluded.label,
          notes=excluded.notes
        """
        cur = self.conn.cursor()
        for ev in events:
            cur.execute(sql, ev.to_row())
            n += 1
        self.conn.commit()
        return n

    def upsert_session_meta(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO sessions_meta (
              session_id, title, source_product, source_surface, cwd, started_at, model_default, originator
            ) VALUES (
              :session_id, :title, :source_product, :source_surface, :cwd, :started_at, :model_default, :originator
            )
            ON CONFLICT(session_id) DO UPDATE SET
              title=COALESCE(excluded.title, sessions_meta.title),
              source_surface=COALESCE(excluded.source_surface, sessions_meta.source_surface),
              cwd=COALESCE(excluded.cwd, sessions_meta.cwd),
              started_at=COALESCE(sessions_meta.started_at, excluded.started_at),
              model_default=COALESCE(excluded.model_default, sessions_meta.model_default),
              originator=COALESCE(excluded.originator, sessions_meta.originator)
            """,
            row,
        )
        self.conn.commit()

    def record_ingest_run(
        self,
        channel: str,
        started_at: str,
        finished_at: str,
        files_seen: int,
        events_upserted: int,
        events_skipped: int,
        notes: str = "",
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO ingest_runs (channel, started_at, finished_at, files_seen, events_upserted, events_skipped, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (channel, started_at, finished_at, files_seen, events_upserted, events_skipped, notes),
        )
        self.conn.commit()

    def count_events(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0])

    def fetch_all_events(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM usage_events ORDER BY ts_utc DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def fetch_session_meta(self) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM sessions_meta").fetchall()
        return {r["session_id"]: dict(r) for r in rows}

    def reprice_all(self, price_fn) -> int:
        """Recompute cost fields for all events via price_fn(row)->dict updates."""
        rows = self.fetch_all_events()
        n = 0
        for row in rows:
            updates = price_fn(row)
            if not updates:
                continue
            self.conn.execute(
                """
                UPDATE usage_events SET
                  unit_price_in_per_1m=:unit_price_in_per_1m,
                  unit_price_out_per_1m=:unit_price_out_per_1m,
                  unit_price_cached_in_per_1m=:unit_price_cached_in_per_1m,
                  cost_usd=:cost_usd,
                  pricing_as_of=:pricing_as_of,
                  evidence_class=:evidence_class
                WHERE event_id=:event_id
                """,
                updates,
            )
            n += 1
        self.conn.commit()
        return n
