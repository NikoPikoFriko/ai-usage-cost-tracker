# Changelog

All notable changes to this project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **D9 multi-provider spend plane** (NEW DIRECTION): open `source_product`, `grain`, `money_rail`
- Docs: `docs/SCHEMA.md`, `docs/ADAPTER_PROTOCOL.md`, updated `docs/DIRECTIONS.md`
- UI: dynamic provider filters + **by_rail** / metered_only / all_labeled rollup
- Export totals: `cost_by_rail`, `cost_by_product`, `cost_usd_metered_only`
- Codex rows tagged `grain=turn`, `money_rail=credits|api_metered`
- **Adapter registry** + CLI `ingest list`
- Provider packs: **Codex**, **Perplexity** (seat+CSV), **Gemini** (seat+CSV)
- **Two tracks:** `master` (universal) vs `personal` — [docs/TRACKS.md](docs/TRACKS.md)
- Community contribution path: [docs/PROVIDERS.md](docs/PROVIDERS.md), provider issue/PR templates
- **`funny-export`**: comic anonymizer for shareable fixture packs ([docs/OBFUSCATE.md](docs/OBFUSCATE.md))

### Planned (by wave)
- **U1** Grok (often personal-first, then promote to master)
- **U2** Claude community or maintainer pack
- ChatGPT subscription ledger · PyPI packaging

## [0.1.0] — 2026-08-11

### Added
- Codex local JSONL ingest (`codex_local_session_jsonl`)
- SQLite store with idempotent event upserts
- Pricing join via `config/PRICING_MODELS.csv` (historical fallback to latest rate)
- MAXres static web UI (`web/`) with session → turn drill-down
- CLI: `ingest`, `reprice`, `export-web`, `stats`, `serve`
- pytest suite for cost formula and fixture parse
- Open-source roster: LICENSE (MIT), SECURITY, CONTRIBUTING, CI

[Unreleased]: https://github.com/NikoPikoFriko/ai-usage-cost-tracker/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/NikoPikoFriko/ai-usage-cost-tracker/releases/tag/v0.1.0

