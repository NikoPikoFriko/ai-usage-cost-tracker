# Notes for coding agents

This is a **public open-source** local-first project.

## Rules

- Never commit secrets, `auth.json`, real `tracker.db`, or real session JSONL.
- Default privacy: no full prompt bodies in the DB.
- Dual ledger: rate-card $ ≠ ChatGPT subscription invoice.
- Prefer pytest when changing `cost.py` or adapters.
- Keep docs honest about ChatGPT Plus token limits.

## Commands

```bash
pip install -r requirements.txt
pytest -q
python -m src.cli ingest codex-jsonl
python -m src.cli serve
```

## Layout

- `src/adapters/` — ingest channels  
- `src/cost.py` — pricing join  
- `src/db.py` — SQLite  
- `web/` — static MAXres UI  
