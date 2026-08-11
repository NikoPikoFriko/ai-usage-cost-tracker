# Review roster

**Mode:** PROPOSE ONLY unless human `APPROVE IMPLEMENT <ids>`.  
**Directions:** [docs/DIRECTIONS.md](docs/DIRECTIONS.md) · [SCHEMA.md](docs/SCHEMA.md) · [ADAPTER_PROTOCOL.md](docs/ADAPTER_PROTOCOL.md)

## Product laws

- Local-first; N-way ledger; privacy; small ships; adapter not fork  

## Directions (D\*)

| Id | Track | Status |
|----|--------|--------|
| D1 | Codex MAXres excellence | SEEDED |
| D2 | Honest ChatGPT lane | SEEDED |
| D3 | Opt-in org Usage API | SEEDED |
| D4 | Pricing fidelity | SEEDED |
| D5 | MAXres UX (provider + rails) | SEEDED |
| D6 | Packaging | SEEDED |
| D7 | OSS quality | SEEDED |
| D8 | Non-goals fence | SEEDED |
| **D9** | **Multi-provider spend plane** | **SEEDED / AXIS** |

## Implementation (IU\* + prior I\*)

| Id | maps_to | Sev | Item | Effort | Status |
|----|---------|-----|------|--------|--------|
| **IU0** | D9 | P0 | Docs: D9 + SCHEMA + ADAPTER_PROTOCOL + roster | S | **DONE** (this PR) |
| **IU1** | D9 | P0 | Schema grain/money_rail + nullable tokens + migrate | M | **IN PROGRESS** |
| **IU2** | D9 | P0 | UI multi-provider + by_rail totals | M | **IN PROGRESS** |
| IU3 | D9 | P1 | Adapter protocol code + registry + `ingest --list` | M | PENDING |
| IU4 | D9/U1 | P1 | Grok local sessions adapter | M | PENDING |
| IU5 | D2/D9 | P1 | ChatGPT subscription ledger rows | M | PENDING |
| IU6 | D4/D9 | P2 | Multi-provider pricing docs | S | PENDING |
| IU7 | D9/U2 | P2 | Claude adapter | L | PENDING |
| IU8 | D9/U3 | P2 | Perplexity sub/invoice adapter | M | PENDING |
| I1 | D1 | P1 | Codex model discovery | M | PENDING |
| I2 | D1 | P2 | Incremental ingest | M | PENDING |
| I3 | D4 | P1 | Model alias resolve | S | **IN PR / PENDING REVIEW** |
| I4 | D5 | P1 | Real date filters | S | PENDING |
| I5 | D5 | P2 | Estimate banner | S | PENDING |
| I10 | D7 | P1 | More fixtures | S | PENDING |
| I12 | D1 | P2 | Subagent rollup | M | PENDING |

## Approval log

| When | Decision | Ids | Notes |
|------|----------|-----|-------|
| 2026-08-11 | SEEDED | D1–D8, I\* | Initial |
| 2026-08-11 | NEW DIRECTION | D9, IU0–IU8 | Multi-provider plane |
| 2026-08-11 | APPROVE IMPLEMENT | IU0–IU2 | Plan GO default batch |
