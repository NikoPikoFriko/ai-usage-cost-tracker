# Changelog

All notable changes to this project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned
- ChatGPT subscription / export lane
- Optional OpenAI Usage / Costs API reconciliation
- PyPI package

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

