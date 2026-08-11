# Architecture (v0.1)

```text
┌─────────────────────┐
│ Codex CODEX_HOME    │  sessions/**/rollout-*.jsonl
│ token_count events  │
└──────────┬──────────┘
           │ adapter: src/adapters/codex_jsonl.py
           v
┌─────────────────────┐
│ UsageEvent rows     │  stable event_id hash
└──────────┬──────────┘
           │ price: src/cost.py + config/PRICING_MODELS.csv
           v
┌─────────────────────┐
│ SQLite              │  data/tracker.db
│ usage_events        │
└──────────┬──────────┘
           │ export: src/export_web.py
           v
┌─────────────────────┐
│ web/data.json       │  LIVE payload
│ web/index.html      │  MAXres UI (totals → session → turn)
└─────────────────────┘
```

## Cost formula

```text
cost_usd =
  (input - cached) * R_in / 1e6
+ cached * R_cached / 1e6
+ output * R_out / 1e6
```

Reasoning tokens are already inside `output` for billing — do not add again.

## Dual ledger (product law)

| Rail | Meaning |
|------|---------|
| Rate-card $ | Public API-equivalent estimate |
| Subscription $ | ChatGPT plan seat (future) — separate |
| Org Usage API | Aggregate truth for API keys (future) |

Never silently sum rails that describe the same work.
