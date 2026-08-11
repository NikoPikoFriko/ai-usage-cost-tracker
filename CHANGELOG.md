# Changelog

All notable changes to this project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Developmental directions seed: `docs/DIRECTIONS.md` (D1–D8)
- Review roster seed proposals I1–I12 in `REVIEW_ROSTER.md`

### Planned (by wave)
- **v0.1.x** — Codex hardening + pricing aliases (D1, D4, D7)
- **v0.2** — Honest ChatGPT lane + UX banners (D2, D5)
- **v0.3** — Opt-in Usage/Costs API reconcile (D3)
- **v0.4** — PyPI packaging (D6)

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

