# AGENTS — ai-usage-cost-tracker

**Ops research SSOT:** `D:\PROJECT_CENTER\20_PROJECTS\AI_USAGE_COST_TRACKER\`  
**Contract:** FC-2026-08-10-AI-USAGE-COST

## Rules
- Git + code only here (`D:\Projects\active\ai-usage-cost-tracker`).
- **Never** commit API keys, `auth.json`, full prompts, or cookies.
- Default privacy: no prompt bodies in DB (labels/hashes only).
- Dual ledger: metered API $ ≠ ChatGPT subscription flat fee.
- First live channel: Codex local JSONL (`codex_local_session_jsonl`).

## Commands
```powershell
cd D:\Projects\active\ai-usage-cost-tracker
python -m src.cli ingest codex-jsonl
python -m src.cli export-web
python -m src.cli serve
pytest -q
```
