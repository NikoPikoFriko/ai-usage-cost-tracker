# Adapter protocol

Each AI product is a **provider adapter**. Core never hardcodes a closed product enum.

## Contract

An adapter MUST:

| Requirement | Detail |
|-------------|--------|
| `id` | Stable `ingest_channel` string (e.g. `codex_local_session_jsonl`) |
| `source_product` | Open product id (`codex`, `grok`, …) |
| `discover()` | Optional: yield paths/resources without secrets |
| `parse(...)` | Emit `list[UsageEvent]` |
| Set **grain** | Best honest grain; never upgrade bucket → turn by averaging |
| Set **money_rail** | Honest rail; never label subscription as `api_metered` |
| Privacy | No full prompts by default; no `auth.json` |
| Idempotency | Stable `event_id` for re-ingest |

An adapter SHOULD:

- Document resolution limits in channel notes  
- Prefer OBS provider fields over estimates  
- Ship anonymized fixture under `tests/fixtures/`  

An adapter MUST NOT:

- Upload data  
- Require cloud by default  
- Collapse multi-rail totals  

## Registration

```text
config/channels.yaml     # enabled adapters + path hints
src/adapters/registry.py # id -> loader
python -m src.cli ingest --list
python -m src.cli ingest <adapter_id>
```

## Adding a provider (checklist)

1. Write field map (docs or comment in adapter).  
2. Implement adapter module.  
3. Register in `registry` + `channels.yaml`.  
4. Fixture + pytest.  
5. UI: product appears in filter automatically if data present.  
6. Pricing rows and/or invoice/sub map if needed.  
7. README one-liner under provider waves.

## First-wave adapters

| Id | Product | Grain | Rail (typical) |
|----|---------|-------|----------------|
| `codex_local_session_jsonl` | codex | turn | credits / api_metered |
| `grok_sessions` (U1) | grok | turn | api_metered / native ticks |
| `chatgpt_subscription` | chatgpt | day / period | subscription |
| `claude_*` (U2) | claude | request / export | api_metered |
| `perplexity_*` (U3) | perplexity | period | subscription |
