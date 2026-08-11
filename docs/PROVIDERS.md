# Provider packs (for contributors)

Anyone can add a provider to the **universal** track so others can use it.

## What a provider pack is

Minimal set:

| File | Role |
|------|------|
| `src/adapters/<name>.py` | Parse local/export data → `UsageEvent` |
| `docs/providers/<NAME>.md` | How to install/ingest, honesty limits |
| `tests/fixtures/<name>_*.csv` or `.jsonl` | Anonymized sample |
| Registry entry | `src/adapters/registry.py` + `config/channels.yaml` |
| Test | `tests/test_providers.py` or dedicated file |

## Rules (hard)

1. **Honest grain** — never invent turn-level tokens from a monthly total.  
2. **Honest money_rail** — `subscription` vs `api_metered` vs `shadow_estimate`.  
3. **No secrets** in the PR.  
4. **No full prompts** in fixtures.  
5. **Local-first** — default path is offline files / user-supplied CSV.  
6. **Fixtures from real data?** Run `python -m src.cli funny-export` first ([OBFUSCATE.md](OBFUSCATE.md)), then skim for usernames.  

## Suggested PR title format

```text
provider(<id>): <one-line what it ingests>
```

Examples:

- `provider(codex): local rollout JSONL turn tokens`  
- `provider(perplexity): seat amortization + manual CSV`  
- `provider(gemini): seat/budget + usage CSV`  
- `provider(claude): Anthropic usage export`  

## PR body template

```markdown
## Provider
- product id:
- cli id:
- grain(s):
- money_rail(s):

## Source
How a user gets the data (path, export UI, docs link).

## Honesty
What this does **not** claim.

## Test
How to run the fixture test.
```

## Review process

1. Contributor opens PR → **`master`**.  
2. Maintainer (or you) reviews for schema + honesty + privacy.  
3. Merge only the universal pack — not someone’s personal paths.  

Personal experiments stay on the **`personal`** branch until cleaned for `master` ([TRACKS.md](TRACKS.md)).
