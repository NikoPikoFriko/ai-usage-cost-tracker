# STATUS — ai-usage-cost-tracker

**Updated:** 2026-08-10  
**Contract:** FC-2026-08-10-AI-USAGE-COST  
**Phase:** MVP1 live

## Acceptance

| Check | Status |
|-------|--------|
| Code home `D:\Projects\active\ai-usage-cost-tracker` | OK |
| Schema matches ops usage_event | OK |
| Pricing join + historical fallback | OK |
| Codex JSONL ingest | OK — 278 files, 21362 events, 125 sessions |
| MAXres UI export | OK — `web/data.json` LIVE |
| Privacy (no prompt bodies) | OK |
| Idempotent re-ingest | OK — row count stable |
| pytest | OK — 6 passed |

## Live snapshot (post-reprice)

- **API-equivalent cost (priced):** ~$1642.93 (rate-card; ChatGPT plan rail ≠ bank invoice)
- **Events:** 21362 (20936 priced, 426 GAP unknown model)
- **Sessions:** 125
- **Note:** token totals sum **per-turn billed** input (context re-send) — correct for $ math

## Commands

```powershell
cd D:\Projects\active\ai-usage-cost-tracker
python -m src.cli ingest codex-jsonl
python -m src.cli reprice
python -m src.cli export-web
python -m src.cli serve   # http://127.0.0.1:8765/
```

## Next (MVP1b / MVP2)

1. ChatGPT subscription amortization ledger  
2. Optional OpenAI Usage API buckets  
3. Model alias map for remaining unknown  
