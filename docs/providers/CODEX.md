# Provider: Codex (OpenAI)

| | |
|--|--|
| **CLI id** | `codex-jsonl` |
| **Channel** | `codex_local_session_jsonl` |
| **Product** | `codex` |
| **Grain** | `turn` |
| **Money rail** | `credits` (ChatGPT-plan Codex) or `api_metered` (API-key) |

## Source

Local session rollouts:

```text
%USERPROFILE%\.codex\sessions\**\rollout-*.jsonl
%USERPROFILE%\.codex\archived_sessions\**
# or $CODEX_HOME
```

Parses `token_count` → `last_token_usage` (input/output/cached/reasoning).

## Ingest

```bash
python -m src.cli ingest codex-jsonl
python -m src.cli ingest codex-jsonl --codex-home /path/to/.codex
python -m src.cli ingest codex-jsonl --no-archived --max-files 50
```

## Honesty

- Plan/credits burn is **rate-card API-equivalent**, not necessarily your Stripe invoice.
- Session token totals sum **per-turn billed context** (re-sent each turn).

## Privacy

Does not read `auth.json`. Does not store full prompts.
