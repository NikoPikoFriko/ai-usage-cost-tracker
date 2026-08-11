# AI Usage Cost Tracker

Local-first cost ledger for **ChatGPT + Codex**, MAXres at **token → prompt/turn → session**.

**Ops pack:** `D:\PROJECT_CENTER\20_PROJECTS\AI_USAGE_COST_TRACKER\`  
**Contract:** `FC-2026-08-10-AI-USAGE-COST`

## MVP1 (this repo)

1. Ingest Codex session JSONL (`%USERPROFILE%\.codex\sessions\**\rollout-*.jsonl`)
2. Price turns with `config/PRICING_MODELS.csv`
3. Store SQLite `data/tracker.db`
4. Open MAXres UI `web/index.html` (after `export-web`)

## Quick start

```powershell
cd D:\Projects\active\ai-usage-cost-tracker
python -m pip install -r requirements.txt
python -m src.cli ingest codex-jsonl
python -m src.cli export-web
# open web/index.html  OR:
python -m src.cli serve
```

## Honest limits

| Source | Grain | $ |
|--------|-------|---|
| Codex JSONL | per-turn tokens | API-equivalent via rate card |
| ChatGPT Plus web | not yet | subscription / future MVP2 |
| OpenAI Usage API | not yet | optional MVP1b |

## Privacy

- Does **not** store full prompts by default.
- Does **not** read or copy `auth.json`.
- DB and exports under `data/` are gitignored.
