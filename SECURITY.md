# Security policy

## What this tool does with data

- **Reads** local Codex session JSONL under `CODEX_HOME` (default `~/.codex`).
- **Writes** a local SQLite DB under `data/tracker.db` and `web/data.json` for the UI.
- **Does not** send usage data to any remote server as part of the default CLI.
- **Does not** read `auth.json`, browser cookies, or API keys for ingest.

## What not to commit or paste

- `data/tracker.db`, `web/data.json`
- `.env`, API keys, Admin keys, session cookies
- Full Codex session JSONL dumps (may contain code, paths, and prompts)
- Screenshots of the UI that still show private project paths you care about

## Reporting a vulnerability

If you find a security issue (e.g. accidental secret retention, path traversal when serving files):

1. **Do not** open a public GitHub issue with exploit details.
2. Email **niko@mojehawaje.pl** with a short description and repro steps.
3. Allow reasonable time for a fix before public disclosure.

## Local server note

`python -m src.cli serve` binds to **127.0.0.1** by default. Do not expose it to the public internet without authentication — it serves your local usage export.
