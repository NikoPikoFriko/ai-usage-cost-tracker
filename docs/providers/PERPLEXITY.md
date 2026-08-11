# Provider: Perplexity

| | |
|--|--|
| **CLI id** | `perplexity-manual` |
| **Channel** | `perplexity_manual` |
| **Product** | `perplexity` |
| **Grain** | `subscription_period` and/or CSV `day` |
| **Money rail** | `subscription` · `invoice_line` |

## Why manual?

Perplexity Pro is primarily a **subscription** product. There is no reliable public per-query token ledger equivalent to Codex JSONL. This adapter is **honest low-res**:

1. Monthly seat amortization  
2. Optional CSV of invoice/usage lines you export yourself  

## Ingest

```bash
# Seat only (example Pro ~$20 — use your real amount)
python -m src.cli ingest perplexity-manual --monthly-usd 20 --period 2026-08

# Optional usage/invoice CSV
python -m src.cli ingest perplexity-manual --csv path/to/perplexity.csv

# Both
python -m src.cli ingest perplexity-manual --monthly-usd 20 --period 2026-08 --csv path/to/perplexity.csv
```

### CSV columns

Required: `ts_utc` (or `date`), `model`, `cost_usd` (or `amount`)  
Optional: `session_id`, `input_tokens`, `output_tokens`, `money_rail`, `grain`, `label`, `notes`

See `tests/fixtures/perplexity_sample.csv`.

## Honesty

- Seat row is **subscription**, not tokens.  
- Do not mix into “metered only” totals without labels (UI `by_rail` default).
