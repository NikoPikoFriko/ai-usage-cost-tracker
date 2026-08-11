"""CLI: ingest / reprice / export-web / serve / stats."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.adapters.codex_jsonl import default_codex_home, ingest_codex_jsonl
from src.cost import load_pricing, price_event_fields
from src.db import TrackerDB
from src.export_web import write_web_data

DB_PATH = ROOT / "data" / "tracker.db"
PRICING = ROOT / "config" / "PRICING_MODELS.csv"
WEB_DATA = ROOT / "web" / "data.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def cmd_ingest_codex(args: argparse.Namespace) -> int:
    home = Path(args.codex_home) if args.codex_home else default_codex_home()
    started = _now()
    events, metas, stats = ingest_codex_jsonl(
        codex_home=home,
        pricing_csv=PRICING,
        include_archived=not args.no_archived,
        max_files=args.max_files,
    )
    db = TrackerDB(DB_PATH)
    try:
        before = db.count_events()
        n = db.upsert_events(events)
        for m in metas:
            db.upsert_session_meta(m)
        after = db.count_events()
        db.record_ingest_run(
            channel="codex_local_session_jsonl",
            started_at=started,
            finished_at=_now(),
            files_seen=stats["files_seen"],
            events_upserted=n,
            events_skipped=stats["files_error"],
            notes=json.dumps({"codex_home": stats["codex_home"], "unique_after": after, "before": before}),
        )
    finally:
        db.close()

    print(f"codex_home: {stats['codex_home']}")
    print(f"files_seen: {stats['files_seen']}")
    print(f"events_parsed: {stats['events']}")
    print(f"events_upserted: {n}")
    print(f"db_events_total: {after}")
    print(f"db: {DB_PATH}")
    if args.export:
        payload = write_web_data(DB_PATH, WEB_DATA)
        print(f"web data: {WEB_DATA} ({payload['meta']['data_class']}, {payload['totals']['events_n']} events)")
    return 0


def cmd_reprice(_: argparse.Namespace) -> int:
    rates = load_pricing(PRICING)
    db = TrackerDB(DB_PATH)

    def price_fn(row: dict) -> dict:
        rail = row.get("money_rail") or "unknown"
        # subscription / invoice lines keep adapter cost unless null
        if rail in ("subscription", "invoice_line") and row.get("cost_usd") is not None:
            return {
                "event_id": row["event_id"],
                "unit_price_in_per_1m": row.get("unit_price_in_per_1m"),
                "unit_price_out_per_1m": row.get("unit_price_out_per_1m"),
                "unit_price_cached_in_per_1m": row.get("unit_price_cached_in_per_1m"),
                "cost_usd": row.get("cost_usd"),
                "pricing_as_of": row.get("pricing_as_of"),
                "evidence_class": row.get("evidence_class") or "OBS",
            }
        tin = row.get("input_tokens")
        tout = row.get("output_tokens")
        if tin is None and tout is None:
            return {
                "event_id": row["event_id"],
                "unit_price_in_per_1m": None,
                "unit_price_out_per_1m": None,
                "unit_price_cached_in_per_1m": None,
                "cost_usd": None,
                "pricing_as_of": None,
                "evidence_class": "GAP",
            }
        p = price_event_fields(
            rates,
            model=row["model"],
            ts_utc=row["ts_utc"],
            input_tokens=int(tin or 0),
            output_tokens=int(tout or 0),
            cached_input_tokens=row.get("cached_input_tokens"),
            cache_write_input_tokens=row.get("cache_write_input_tokens"),
        )
        grade = row.get("evidence_class") or "CAND"
        if p["priced"]:
            grade = "CAND" if p.get("rate_evidence") == "CAND" else "OBS"
        else:
            grade = "GAP"
        return {
            "event_id": row["event_id"],
            "unit_price_in_per_1m": p["unit_price_in_per_1m"],
            "unit_price_out_per_1m": p["unit_price_out_per_1m"],
            "unit_price_cached_in_per_1m": p["unit_price_cached_in_per_1m"],
            "cost_usd": p["cost_usd"],
            "pricing_as_of": p["pricing_as_of"],
            "evidence_class": grade,
        }

    try:
        n = db.reprice_all(price_fn)
    finally:
        db.close()
    print(f"repriced: {n}")
    return 0


def cmd_export_web(_: argparse.Namespace) -> int:
    payload = write_web_data(DB_PATH, WEB_DATA)
    t = payload["totals"]
    print(f"wrote {WEB_DATA}")
    print(f"data_class={payload['meta']['data_class']} sessions={t['sessions_n']} events={t['events_n']} cost=${t['cost_usd_priced']}")
    return 0


def cmd_stats(_: argparse.Namespace) -> int:
    if not DB_PATH.exists():
        print("no db yet — run: python -m src.cli ingest codex-jsonl")
        return 1
    db = TrackerDB(DB_PATH)
    try:
        payload = write_web_data(DB_PATH, WEB_DATA)
    finally:
        db.close()
    print(json.dumps(payload["totals"], indent=2))
    print("gaps:", payload["gaps"])
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    if not WEB_DATA.exists():
        write_web_data(DB_PATH, WEB_DATA)
    web_dir = ROOT / "web"

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(web_dir), **kw)

        def log_message(self, fmt, *log_args):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % log_args))

    host = args.host
    port = args.port
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"serving {web_dir} at http://{host}:{port}/  (index.html)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstop")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ai-usage-cost-tracker", description="Local AI usage cost tracker (ChatGPT+Codex)")
    sub = p.add_subparsers(dest="cmd", required=True)

    ing = sub.add_parser("ingest", help="Ingest a channel")
    ing_sub = ing.add_subparsers(dest="channel", required=True)
    c = ing_sub.add_parser("codex-jsonl", help="Parse ~/.codex sessions JSONL")
    c.add_argument("--codex-home", default=None, help="Override CODEX_HOME")
    c.add_argument("--no-archived", action="store_true")
    c.add_argument("--max-files", type=int, default=None, help="Limit files (debug)")
    c.add_argument("--export", action="store_true", default=True)
    c.add_argument("--no-export", action="store_false", dest="export")
    c.set_defaults(func=cmd_ingest_codex)

    r = sub.add_parser("reprice", help="Recompute costs from pricing CSV")
    r.set_defaults(func=cmd_reprice)

    e = sub.add_parser("export-web", help="Write web/data.json from DB")
    e.set_defaults(func=cmd_export_web)

    s = sub.add_parser("stats", help="Print totals")
    s.set_defaults(func=cmd_stats)

    srv = sub.add_parser("serve", help="Local HTTP server for web/")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8765)
    srv.set_defaults(func=cmd_serve)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
