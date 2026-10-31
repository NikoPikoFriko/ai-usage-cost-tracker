"""SQLite store for multi-provider usage_events."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable

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
  grain TEXT NOT NULL DEFAULT 'unknown',
  money_rail TEXT NOT NULL DEFAULT 'unknown',
  prompt_text_hash TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  cached_input_tokens INTEGER,
  reasoning_tokens INTEGER,
  cache_write_input_tokens INTEGER,
  total_tokens INTEGER,
  unit_price_in_per_1m REAL,
  unit_price_out_per_1m REAL,
  unit_price_cached_in_per_1m REAL,
  cost_usd REAL,
  amount_native REAL,
  currency TEXT,
  pricing_as_of TEXT,
  billing_identity TEXT,
  service_tier TEXT,
  evidence_class TEXT NOT NULL,
  ingest_channel TEXT NOT NULL,
  raw_ref TEXT,
  notes TEXT,
  label TEXT,
  cash_source_record_id TEXT,
  cash_status TEXT,
  cash_merchant TEXT
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

CREATE TABLE IF NOT EXISTS schema_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cash_cross_references (
  link_id TEXT PRIMARY KEY,
  invoice_event_id TEXT NOT NULL,
  settlement_event_id TEXT NOT NULL,
  relation TEXT NOT NULL CHECK (relation IN ('settles', 'refunds', 'partial_settlement', 'candidate_match')),
  status TEXT NOT NULL CHECK (status IN ('candidate', 'confirmed', 'rejected')),
  confidence REAL,
  matched_on TEXT NOT NULL DEFAULT '',
  confirmed_by TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cash_links_invoice ON cash_cross_references(invoice_event_id);
CREATE INDEX IF NOT EXISTS idx_cash_links_settlement ON cash_cross_references(settlement_event_id);

CREATE TABLE IF NOT EXISTS cash_link_history (
  history_id INTEGER PRIMARY KEY AUTOINCREMENT,
  link_id TEXT NOT NULL,
  action TEXT NOT NULL,
  prior_status TEXT,
  status TEXT NOT NULL,
  changed_at TEXT NOT NULL,
  snapshot_json TEXT NOT NULL
);
"""

# Columns expected after migrate
_EXPECTED_COLS = {
    "grain",
    "money_rail",
}


class TrackerDB:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        cols = {
            r[1]
            for r in self.conn.execute("PRAGMA table_info(usage_events)").fetchall()
        }
        if "grain" not in cols:
            self.conn.execute(
                "ALTER TABLE usage_events ADD COLUMN grain TEXT NOT NULL DEFAULT 'unknown'"
            )
        if "money_rail" not in cols:
            self.conn.execute(
                "ALTER TABLE usage_events ADD COLUMN money_rail TEXT NOT NULL DEFAULT 'unknown'"
            )
        for column, declaration in (
            ("amount_native", "REAL"),
            ("currency", "TEXT"),
            ("cash_source_record_id", "TEXT"),
            ("cash_status", "TEXT"),
            ("cash_merchant", "TEXT"),
        ):
            if column not in cols:
                self.conn.execute(
                    f"ALTER TABLE usage_events ADD COLUMN {column} {declaration}"
                )
        # Re-read cols after ALTER
        cols = {
            r[1]
            for r in self.conn.execute("PRAGMA table_info(usage_events)").fetchall()
        }
        if "money_rail" in cols:
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_rail ON usage_events(money_rail)"
            )
        # Backfill codex-like rows missing grain/rail
        if "grain" in cols:
            self.conn.execute(
                """
                UPDATE usage_events
                SET grain = 'turn'
                WHERE (grain IS NULL OR grain = '' OR grain = 'unknown')
                  AND source_product = 'codex'
                  AND ingest_channel LIKE 'codex%'
                """
            )
        if "money_rail" in cols:
            self.conn.execute(
                """
                UPDATE usage_events
                SET money_rail = CASE
                  WHEN billing_identity = 'api_org' THEN 'api_metered'
                  WHEN source_product = 'codex' THEN 'credits'
                  ELSE COALESCE(NULLIF(money_rail, 'unknown'), 'unknown')
                END
                WHERE money_rail IS NULL OR money_rail = '' OR money_rail = 'unknown'
                """
            )
        self.conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('version', '0.3-cash-trail')"
        )

    def close(self) -> None:
        self.conn.close()

    def upsert_events(self, events: Iterable[UsageEvent]) -> int:
        n = 0
        sql = """
        INSERT INTO usage_events (
          event_id, source_product, source_surface, session_id, parent_event_id,
          ts_utc, model, grain, money_rail, prompt_text_hash,
          input_tokens, output_tokens, cached_input_tokens, reasoning_tokens,
          cache_write_input_tokens, total_tokens,
          unit_price_in_per_1m, unit_price_out_per_1m, unit_price_cached_in_per_1m,
          cost_usd, amount_native, currency, pricing_as_of, billing_identity, service_tier,
          evidence_class, ingest_channel, raw_ref, notes, label,
          cash_source_record_id, cash_status, cash_merchant
        ) VALUES (
          :event_id, :source_product, :source_surface, :session_id, :parent_event_id,
          :ts_utc, :model, :grain, :money_rail, :prompt_text_hash,
          :input_tokens, :output_tokens, :cached_input_tokens, :reasoning_tokens,
          :cache_write_input_tokens, :total_tokens,
          :unit_price_in_per_1m, :unit_price_out_per_1m, :unit_price_cached_in_per_1m,
          :cost_usd, :amount_native, :currency, :pricing_as_of, :billing_identity, :service_tier,
          :evidence_class, :ingest_channel, :raw_ref, :notes, :label,
          :cash_source_record_id, :cash_status, :cash_merchant
        )
        ON CONFLICT(event_id) DO UPDATE SET
          cost_usd=excluded.cost_usd,
          unit_price_in_per_1m=excluded.unit_price_in_per_1m,
          unit_price_out_per_1m=excluded.unit_price_out_per_1m,
          unit_price_cached_in_per_1m=excluded.unit_price_cached_in_per_1m,
          pricing_as_of=excluded.pricing_as_of,
          evidence_class=excluded.evidence_class,
          model=excluded.model,
          grain=excluded.grain,
          money_rail=excluded.money_rail,
          label=excluded.label,
          notes=excluded.notes,
          input_tokens=excluded.input_tokens,
          output_tokens=excluded.output_tokens,
          cached_input_tokens=excluded.cached_input_tokens,
          amount_native=excluded.amount_native,
          currency=excluded.currency,
          cash_source_record_id=excluded.cash_source_record_id,
          cash_status=excluded.cash_status,
          cash_merchant=excluded.cash_merchant
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

    def upsert_cash_link(self, link: dict[str, Any]) -> None:
        from datetime import datetime, timezone
        import json

        required = {
            "link_id", "invoice_event_id", "settlement_event_id", "relation",
            "status", "confidence", "matched_on", "confirmed_by",
        }
        missing = required - link.keys()
        if missing:
            raise ValueError(f"Missing cash link fields: {', '.join(sorted(missing))}")
        if link["relation"] not in {
            "settles", "refunds", "partial_settlement", "candidate_match"
        }:
            raise ValueError(f"Invalid cash link relation: {link['relation']}")
        if link["status"] not in {"candidate", "confirmed", "rejected"}:
            raise ValueError(f"Invalid cash link status: {link['status']}")
        if link["status"] == "confirmed" and not link["confirmed_by"]:
            raise ValueError("Confirmed cash links require an operator or explicit rule")
        if link["status"] == "confirmed" and link["confirmed_by"] != "operator" and not (
            str(link["confirmed_by"]).startswith("rule:")
            and len(str(link["confirmed_by"])) > len("rule:")
        ):
            raise ValueError("Confirmed cash links require operator or rule:<id>")
        surfaces = []
        for event_id in (link["invoice_event_id"], link["settlement_event_id"]):
            exists = self.conn.execute(
                "SELECT source_surface, money_rail FROM usage_events WHERE event_id=?",
                (event_id,),
            ).fetchone()
            if not exists:
                raise ValueError(f"Cash link references unknown event: {event_id}")
            if exists["money_rail"] != "invoice_line" or exists["source_surface"] not in {
                "provider_invoice", "bank_statement"
            }:
                raise ValueError("Cash links may reference only invoice/bank cash evidence")
            surfaces.append(exists["source_surface"])
        if surfaces != ["provider_invoice", "bank_statement"]:
            raise ValueError("Cash links must point from an invoice to a bank-statement row")

        now = datetime.now(timezone.utc).isoformat()
        current = self.conn.execute(
            "SELECT * FROM cash_cross_references WHERE link_id=?",
            (link["link_id"],),
        ).fetchone()
        created_at = current["created_at"] if current else now
        values = {
            **link,
            "created_at": created_at,
            "updated_at": now,
        }
        snapshot = json.dumps(values, sort_keys=True)
        if current and all(current[key] == values[key] for key in link):
            return
        self.conn.execute(
            """
            INSERT INTO cash_cross_references (
              link_id, invoice_event_id, settlement_event_id, relation, status,
              confidence, matched_on, confirmed_by, created_at, updated_at
            ) VALUES (
              :link_id, :invoice_event_id, :settlement_event_id, :relation, :status,
              :confidence, :matched_on, :confirmed_by, :created_at, :updated_at
            )
            ON CONFLICT(link_id) DO UPDATE SET
              invoice_event_id=excluded.invoice_event_id,
              settlement_event_id=excluded.settlement_event_id,
              relation=excluded.relation,
              status=excluded.status,
              confidence=excluded.confidence,
              matched_on=excluded.matched_on,
              confirmed_by=excluded.confirmed_by,
              updated_at=excluded.updated_at
            """,
            values,
        )
        self.conn.execute(
            """
            INSERT INTO cash_link_history (
              link_id, action, prior_status, status, changed_at, snapshot_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                link["link_id"],
                "updated" if current else "created",
                current["status"] if current else None,
                link["status"],
                now,
                snapshot,
            ),
        )
        self.conn.commit()

    def fetch_cash_links(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM cash_cross_references ORDER BY created_at, link_id"
        ).fetchall()
        return [dict(row) for row in rows]

    def fetch_session_meta(self) -> dict[str, dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM sessions_meta").fetchall()
        return {r["session_id"]: dict(r) for r in rows}

    def reprice_all(self, price_fn) -> int:
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
