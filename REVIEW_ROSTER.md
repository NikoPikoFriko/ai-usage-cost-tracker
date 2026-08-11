# Review roster (Grok Web BUILD)

**Mode:** PROPOSE ONLY — comments / checklist. No code until human `APPROVE IMPLEMENT <ids>`.

**Repo:** https://github.com/NikoPikoFriko/ai-usage-cost-tracker  
**Base:** master @ v0.1.0  
**Directions seed:** [docs/DIRECTIONS.md](docs/DIRECTIONS.md)

## How to use

1. **Directions (D\*)** = product north stars (Principal-seeded). Rarely change without `NEW DIRECTION`.  
2. **Items (I\*)** = concrete implementation proposals (Web BUILD or humans). Must `maps_to` a D-track.  
3. Human: `APPROVE I1 I3` / `REJECT I2` / `DEFER I4` / `APPROVE IMPLEMENT I1`.  
4. Local implementer ships only approved **I\*** ids.

## Product laws (do not violate)

- Local-first; no cloud upload by default  
- Dual ledger: rate-card $ ≠ ChatGPT subscription invoice  
- No full prompts by default; never touch auth.json  
- Small, shippable diffs; no multi-vendor FinOps scope creep  

---

## Developmental directions (seeded — D\*)

| Id | Track | Wave | Goal (one line) | Status |
|----|--------|------|-----------------|--------|
| D1 | Codex MAXres excellence | v0.1.x | Robust local turn tokens, models, rollups | **SEEDED** |
| D2 | Honest ChatGPT lane | v0.2 | Seat $ + optional shadow tokens; no fake invoices | **SEEDED** |
| D3 | API/org reconciliation | v0.3 | Opt-in Usage/Costs buckets; no double-count | **SEEDED** |
| D4 | Pricing fidelity | v0.1.x | Aliases, tiers, refresh from official rates | **SEEDED** |
| D5 | MAXres UX polish | v0.2–0.4 | Date filters, export, estimate vs cash banners | **SEEDED** |
| D6 | Packaging & install | v0.4 | PyPI + `ai-usage-cost` entrypoint | **SEEDED** |
| D7 | Quality & trust (OSS) | always | CI, fixtures, safe contrib path | **SEEDED** |
| D8 | Explicit non-goals | fence | No SaaS/cookie scrape/multi-vendor v1 | **SEEDED** |

Details: **docs/DIRECTIONS.md**.

---

## Implementation roster (I\*) — seed proposals for review

Web BUILD may **refine, split, or add** I-items; do not delete D-tracks.

| Id | maps_to | Severity | Area | Problem | Proposed change | Effort | Status |
|----|---------|----------|------|---------|-----------------|--------|--------|
| I1 | D1 | P1 | correctness | Model often late/unknown in JSONL | Improve model discovery order; config.toml default fallback; tests | M | PENDING |
| I2 | D1 | P2 | performance | Full re-scan of all rollouts every ingest | `--since` / mtime watermark; document re-ingest | M | PENDING |
| I3 | D4 | P1 | correctness | Aliases (e.g. codex-auto-review) and tiers underpriced | Alias table + optional service_tier column; docs | M | PENDING |
| I4 | D5 | P1 | UX | Period filters are cosmetic on live export | Real Today/7d/30d filter on event ts in web JS | S | PENDING |
| I5 | D5 | P2 | UX | Easy to misread rate-card $ as invoice | Banner: billing_identity + “API-equivalent estimate” | S | PENDING |
| I6 | D2 | P1 | product | No ChatGPT surface at all | Design + stub: subscription ledger schema (no fake tokens) | M | PENDING |
| I7 | D2 | P2 | product | Plus export shadow cost unclear | Spec for export→tiktoken HYP path (implement later) | S | PENDING |
| I8 | D3 | P2 | product | No org bill cross-check | Spec opt-in Usage API adapter (env key, bucket grain) | M | PENDING |
| I9 | D6 | P2 | packaging | Clone-only install | Harden pyproject entrypoint; document pipx/editable install | S | PENDING |
| I10 | D7 | P1 | tests | Few real-shape fixtures | Add anonymized multi-turn fixture + regression tests | S | PENDING |
| I11 | D7 | P2 | docs | Screenshots missing for OSS | Redacted MOCK screenshots in README | S | PENDING |
| I12 | D1 | P2 | UX | Subagent sessions flood session list | Rollup/hide subagent option; parent thread join | M | PENDING |

---

## Approval log

| When | Decision | Ids | Notes |
|------|----------|-----|-------|
| 2026-08-11 | SEEDED | D1–D8, I1–I12 | Principal seed; all I\* PENDING |

---

## Web BUILD instructions (short)

```text
Refine REVIEW_ROSTER.md implementation items I1–I12 against docs/DIRECTIONS.md.
You may split/add I-items with maps_to Dx. Do not drop dual-ledger or add SaaS.
MODE: comment / propose only. No commits unless human APPROVE IMPLEMENT.
End: Awaiting APPROVE / REJECT / DEFER per I-id.
```
