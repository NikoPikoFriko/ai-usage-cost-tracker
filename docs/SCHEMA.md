# Schema — multi-provider usage / cost events

## Design goals

1. One table shape for **all** agents.  
2. **Grain** and **money_rail** always explicit.  
3. Tokens optional (subscription/invoice rows).  
4. Trust fields never optional for new writers.

## `usage_events` (logical)

| Field | Required | Notes |
|-------|----------|--------|
| `event_id` | yes | Stable hash; idempotent upsert |
| `source_product` | yes | Open string: `codex`, `chatgpt`, `grok`, `claude`, `perplexity`, … |
| `source_surface` | no | cli, web, api, desktop, … |
| `session_id` | yes | Provider-native or synthetic |
| `parent_event_id` | no | Tool/subagent child |
| `ts_utc` | yes | ISO-8601 |
| `model` | yes | Or `subscription` / `unknown` |
| `grain` | yes | See enum |
| `money_rail` | yes | See enum |
| `input_tokens` | no | Null if not applicable |
| `output_tokens` | no | Null if not applicable |
| `cached_input_tokens` | no | |
| `reasoning_tokens` | no | Diagnostic; do not double-bill |
| `cache_write_input_tokens` | no | |
| `total_tokens` | no | |
| `unit_price_*` | no | From rate card when metered |
| `cost_usd` | no | Null = GAP / unpriced |
| `pricing_as_of` | no | |
| `billing_identity` | no | plan / org / account label |
| `service_tier` | no | standard / fast / batch |
| `evidence_class` | yes | OBS / NIKO / CAND / HYP / GAP |
| `ingest_channel` | yes | Adapter id |
| `raw_ref` | no | Local path pointer only |
| `label` | no | Short UI label, not full prompt |
| `notes` | no | |

## Enums

### `grain`

`turn` · `request` · `session` · `day` · `subscription_period` · `bucket` · `unknown`

### `money_rail`

| Value | Meaning |
|-------|---------|
| `api_metered` | Token × rate card or provider metered bill |
| `subscription` | Seat / plan fee amortization |
| `credits` | Plan credits / included usage burn (API-equivalent often estimate) |
| `shadow_estimate` | HYP “if this were API” |
| `invoice_line` | From invoice/export line item |
| `unknown` | Not classified |

## Rollup modes (UI / export)

| Mode | Behavior |
|------|----------|
| **`by_rail` (default)** | Separate $ totals per `money_rail`; no silent mix |
| **`metered_only`** | Sum only `api_metered` (+ optional explicit credits policy later) |
| **`all_labeled`** | Grand total **plus** mandatory rail breakdown |

## Pricing rule

```text
IF money_rail in (api_metered, credits, shadow_estimate)
   AND input_tokens/output_tokens present
   AND model in rate card
THEN cost_usd = formula
ELSE IF money_rail in (subscription, invoice_line) AND cost_usd provided by adapter
THEN keep adapter cost
ELSE cost_usd = null (GAP)
```

Reasoning tokens are inside billable output when metered — never add twice.

## Migration from v0.1

- Existing Codex rows: `grain=turn`, `money_rail=credits` (ChatGPT-plan Codex) or `api_metered` if known API-key.  
- Token columns become nullable for new subscription rows.  
- Local DB: `ALTER` add columns; re-ingest or `reprice` as needed.
