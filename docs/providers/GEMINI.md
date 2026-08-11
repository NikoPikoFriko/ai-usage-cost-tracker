# Provider: Gemini (Google)

| | |
|--|--|
| **CLI id** | `gemini-manual` |
| **Channel** | `gemini_manual` |
| **Product** | `gemini` |
| **Grain** | `subscription_period` and/or CSV `request` |
| **Money rail** | `subscription` · `api_metered` · `invoice_line` |

## Why manual first?

Google AI Studio / Gemini Advanced / Vertex each expose different billing surfaces. v0.1 adapter is **local-first honest**:

1. Monthly seat or prepaid budget amortization  
2. Optional CSV export of API usage (when you have token + $ columns)

Future: native Vertex/AI Studio export parsers (still offline file ingest).

## Ingest

```bash
python -m src.cli ingest gemini-manual --monthly-usd 20 --period 2026-08
python -m src.cli ingest gemini-manual --csv path/to/gemini_usage.csv
```

### CSV columns

Same as Perplexity helper: `ts_utc`, `model`, `cost_usd`, optional tokens.

If tokens present without cost, rows may show **GAP** until rates are added to `PRICING_MODELS.csv`.

See `tests/fixtures/gemini_sample.csv`.

## Honesty

- Advanced/subscription is not the same as pay-as-you-go API.  
- Use `money_rail` column in CSV when lines are invoices vs metered.
