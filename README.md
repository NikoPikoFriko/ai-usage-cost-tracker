# AI Usage Cost Tracker

**Local-first** cost ledger for **OpenAI Codex** (and planned ChatGPT surfaces): tokens → USD at **turn / session** resolution.

```text
your machine  →  ingest Codex JSONL  →  SQLite  →  price with rate card  →  MAXres web UI
```

No cloud account required. Your usage data stays on disk.

[![CI](https://github.com/NikoPikoFriko/ai-usage-cost-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/NikoPikoFriko/ai-usage-cost-tracker/actions/workflows/ci.yml)

## Features (v0.1)

- **Codex local ingest** — reads `~/.codex/sessions/**/rollout-*.jsonl` (`token_count` / last-turn usage)
- **Deterministic pricing** — `config/PRICING_MODELS.csv` ($ / 1M tokens)
- **MAXres UI** — totals → sessions → turns; filters; GAP panel for unpriced models
- **Privacy default** — no full prompt bodies; does not read `auth.json`
- **Idempotent re-ingest** — stable `event_id` hashes; safe to re-run

## Requirements

- Python **3.11+** (tested on 3.12)
- OpenAI **Codex** CLI / desktop that writes local session JSONL
- Windows, macOS, or Linux

## Quick start

```bash
git clone https://github.com/NikoPikoFriko/ai-usage-cost-tracker.git
cd ai-usage-cost-tracker

python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
python -m src.cli ingest codex-jsonl
python -m src.cli serve
```

Open **http://127.0.0.1:8765/**

> Prefer `serve` over opening `web/index.html` via `file://` — browsers block `fetch` of `data.json` on file URLs.

### Useful commands

```bash
python -m src.cli ingest codex-jsonl          # parse sessions (+ archived)
python -m src.cli ingest codex-jsonl --no-archived
python -m src.cli reprice                    # after editing PRICING_MODELS.csv
python -m src.cli export-web                 # refresh web/data.json
python -m src.cli stats
python -m src.cli serve --port 8765
pytest -q
```

### Custom Codex home

```bash
# env
set CODEX_HOME=C:\path\to\.codex          # Windows cmd
$env:CODEX_HOME="C:\path\to\.codex"       # PowerShell
export CODEX_HOME="$HOME/.codex"          # bash

# or flag
python -m src.cli ingest codex-jsonl --codex-home /path/to/.codex
```

## Honest limits (read this)

| Source | Token grain | What $ means |
|--------|-------------|--------------|
| **Codex local JSONL** | Per turn (when `token_count` exists) | **API-equivalent** from public rate card |
| **ChatGPT Plus / web chat** | Not official per-prompt tokens | Not supported yet (subscription ≠ token invoice) |
| **OpenAI org Usage API** | Time buckets | Not in v0.1 |

- If you use Codex with a **ChatGPT plan**, local $ is a **shadow / rate-card estimate**, not necessarily your Stripe invoice.
- Session token totals sum **per-turn billed input** (context re-sent each turn). That can look large; it matches how API billing works.
- Pricing CSV is a **snapshot** — update from [OpenAI pricing](https://developers.openai.com/api/docs/pricing) when models change.
- Unknown models show as **GAP** until you add a row to `config/PRICING_MODELS.csv` and run `reprice`.

## Privacy

- Stores turn labels like `turn-3`, token counts, model ids, session ids, local file paths as `raw_ref`.
- Does **not** ingest prompt text by default.
- Does **not** open `auth.json` or API keys.
- `data/tracker.db` and `web/data.json` are **gitignored** — never commit them.

See [SECURITY.md](SECURITY.md).

## Project layout

```text
config/PRICING_MODELS.csv   # rate card
src/                        # CLI + adapters + cost + sqlite
web/                        # MAXres static UI
tests/                      # pytest
```

## Roadmap

- [x] v0.1 Codex JSONL + local UI  
- [ ] ChatGPT subscription / export lane (honest dual ledger)  
- [ ] Optional OpenAI Usage / Costs API reconciliation  
- [ ] `pip install` / PyPI package  
- [ ] macOS / Linux CI matrix smoke  

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome.

## License

[MIT](LICENSE) © 2026 NIKODEM PIKOR

## Disclaimer

Not affiliated with OpenAI. Pricing and product surfaces change; treat numbers as **estimates** for personal insight, not accounting or tax advice.

