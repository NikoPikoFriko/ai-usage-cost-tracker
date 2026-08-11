# Funny export — public-safe dataset pack

**One-liner:** Same shape, same analytics value — private fields get hilariously obfuscated so the pack is public-safe.

## What it does

```text
real tracker.db / data.json
        │
        ▼
  funny-export (local)
        │
        ▼
exports/funny/<name>/
  data.json       # web dashboard shape, data_class=FUNNY_PUBLIC
  events.jsonl    # one event per line
  README.md       # human summary
```

| Kept (useful) | Scrubbed (comic) |
|---------------|------------------|
| tokens in/out/cached | session titles |
| cost_usd | labels / notes |
| model | raw_ref / cwd paths |
| source_product / channel | real UUIDs / event ids |
| money_rail / grain | billing_identity free text |
| structure of sessions | anything that looks like a personal path |

**Not encryption.** Discard the mapping; do not publish originals.

## CLI

```bash
# from local DB (after ingest)
python -m src.cli funny-export

# options
python -m src.cli funny-export --name demo_public --shift-days 90
python -m src.cli funny-export --from-json web/data.json --out exports/funny
python -m src.cli funny-export --from-db data/tracker.db --salt "my-run-2026-08"
```

| Flag | Meaning |
|------|---------|
| `--name` | Pack folder name |
| `--out` | Parent directory (default `exports/funny`) |
| `--salt` | Changes the comic vocabulary mapping for the run |
| `--shift-days` | Optional calendar shift (extra scrub) |

## Use in OSS / CI

- Commit **only** funny packs or hand-made anonymized fixtures under `tests/fixtures/`.  
- Never commit live `data/tracker.db`.  
- Provider pack authors: generate funny fixtures from real local data, then PR the pack.

## Privacy checklist before you share

- [ ] Open `events.jsonl` and search for your username, `D:\`, company names  
- [ ] Spot-check session titles are jokes  
- [ ] Confirm token/cost totals still look plausible for demos  
