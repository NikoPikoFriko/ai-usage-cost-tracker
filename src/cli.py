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

from src.adapters.registry import list_adapters, run_adapter
from src.cost import load_pricing, price_event_fields
from src.db import TrackerDB
from src.export_web import write_web_data
from src.obfuscate import (
    load_payload_from_db,
    load_payload_from_json,
    write_funny_pack,
)

DB_PATH = ROOT / "data" / "tracker.db"
PRICING = ROOT / "config" / "PRICING_MODELS.csv"
WEB_DATA = ROOT / "web" / "data.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _persist_result(channel: str, result, export: bool) -> int:
    db = TrackerDB(DB_PATH)
    try:
        before = db.count_events()
        n = db.upsert_events(result.events)
        for m in result.session_metas:
            db.upsert_session_meta(m)
        after = db.count_events()
        stats = result.stats or {}
        db.record_ingest_run(
            channel=channel,
            started_at=_now(),
            finished_at=_now(),
            files_seen=int(stats.get("files_seen") or 0),
            events_upserted=n,
            events_skipped=int(stats.get("files_error") or 0),
            notes=json.dumps({"stats": stats, "before": before, "after": after}),
        )
    finally:
        db.close()
    print(json.dumps(result.stats, indent=2, default=str))
    print(f"events_upserted: {n}")
    print(f"db_events_total: {after}")
    print(f"db: {DB_PATH}")
    if export:
        payload = write_web_data(DB_PATH, WEB_DATA)
        print(
            f"web data: {WEB_DATA} ({payload['meta']['data_class']}, "
            f"{payload['totals']['events_n']} events)"
        )
    return 0


def cmd_ingest_list(_: argparse.Namespace) -> int:
    for row in list_adapters():
        print(f"{row['cli_id']:20}  product={row['product']:12}  {row['description']}")
    return 0


def cmd_ingest_codex(args: argparse.Namespace) -> int:
    result = run_adapter(
        "codex-jsonl",
        codex_home=Path(args.codex_home) if args.codex_home else None,
        pricing_csv=PRICING,
        include_archived=not args.no_archived,
        max_files=args.max_files,
    )
    return _persist_result("codex_local_session_jsonl", result, args.export)


def cmd_ingest_perplexity(args: argparse.Namespace) -> int:
    result = run_adapter(
        "perplexity-manual",
        monthly_usd=args.monthly_usd,
        period=args.period,
        csv_path=Path(args.csv) if args.csv else None,
    )
    return _persist_result("perplexity_manual", result, args.export)


def cmd_ingest_gemini(args: argparse.Namespace) -> int:
    result = run_adapter(
        "gemini-manual",
        monthly_usd=args.monthly_usd,
        period=args.period,
        csv_path=Path(args.csv) if args.csv else None,
    )
    return _persist_result("gemini_manual", result, args.export)


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


def cmd_funny_export(args: argparse.Namespace) -> int:
    """
    Real usage payload → public-safe funny pack (same schema, private fields comic).
    """
    if args.from_json:
        payload = load_payload_from_json(Path(args.from_json))
    elif args.from_db:
        payload = load_payload_from_db(Path(args.from_db))
    elif DB_PATH.exists():
        payload = load_payload_from_db(DB_PATH)
    elif WEB_DATA.exists():
        payload = load_payload_from_json(WEB_DATA)
    else:
        print("No input: run ingest first, or pass --from-db / --from-json", file=sys.stderr)
        return 1

    salt = args.salt or "public-funny-pack"
    out = Path(args.out) if args.out else (ROOT / "exports" / "funny")
    paths = write_funny_pack(
        payload,
        out,
        salt=salt,
        shift_days=int(args.shift_days or 0),
        name=args.name or "funny_pack",
    )
    print(f"funny pack: {paths['dir']}")
    print(f"  data.json     → {paths['data_json']}")
    print(f"  events.jsonl  → {paths['events_jsonl']}")
    print(f"  README.md     → {paths['readme']}")
    print("Remember: originals stay private; this pack is for sharing/tests only.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="ai-usage-cost-tracker",
        description="Local multi-provider AI spend observatory (Codex, Perplexity, Gemini, …)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    ing = sub.add_parser("ingest", help="Ingest a provider adapter")
    ing_sub = ing.add_subparsers(dest="channel", required=True)

    lst = ing_sub.add_parser("list", help="List registered adapters")
    lst.set_defaults(func=cmd_ingest_list)

    c = ing_sub.add_parser("codex-jsonl", help="Codex local session JSONL")
    c.add_argument("--codex-home", default=None, help="Override CODEX_HOME")
    c.add_argument("--no-archived", action="store_true")
    c.add_argument("--max-files", type=int, default=None, help="Limit files (debug)")
    c.add_argument("--export", action="store_true", default=True)
    c.add_argument("--no-export", action="store_false", dest="export")
    c.set_defaults(func=cmd_ingest_codex)

    px = ing_sub.add_parser("perplexity-manual", help="Perplexity seat + optional CSV")
    px.add_argument("--monthly-usd", type=float, default=None)
    px.add_argument("--period", default=None, help="YYYY-MM")
    px.add_argument("--csv", default=None, help="Usage/invoice CSV path")
    px.add_argument("--export", action="store_true", default=True)
    px.add_argument("--no-export", action="store_false", dest="export")
    px.set_defaults(func=cmd_ingest_perplexity)

    ge = ing_sub.add_parser("gemini-manual", help="Gemini seat/budget + optional CSV")
    ge.add_argument("--monthly-usd", type=float, default=None)
    ge.add_argument("--period", default=None, help="YYYY-MM")
    ge.add_argument("--csv", default=None, help="Usage/invoice CSV path")
    ge.add_argument("--export", action="store_true", default=True)
    ge.add_argument("--no-export", action="store_false", dest="export")
    ge.set_defaults(func=cmd_ingest_gemini)

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

    fun = sub.add_parser(
        "funny-export",
        help="Anonymize usage data into a shareable comic fixture pack",
    )
    fun.add_argument("--from-db", default=None, help="Path to tracker.db (default: data/tracker.db)")
    fun.add_argument("--from-json", default=None, help="Path to web/data.json-shaped file")
    fun.add_argument("--out", default=None, help="Output parent dir (default: exports/funny)")
    fun.add_argument("--name", default="funny_pack", help="Pack folder name")
    fun.add_argument(
        "--salt",
        default=None,
        help="Run salt for comic mapping (default fixed public salt; change per export if you like)",
    )
    fun.add_argument(
        "--shift-days",
        type=int,
        default=0,
        help="Shift all timestamps by N days (extra calendar scrub)",
    )
    fun.set_defaults(func=cmd_funny_export)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
