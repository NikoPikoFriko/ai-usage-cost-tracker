# Developmental directions (seeded)

**Status:** Principal-seeded · open for Web BUILD refinement  
**Product:** AI Usage Cost Tracker · Path A open source · local-first  
**As of:** v0.1.0 / 2026-08-11  
**Not a commitment:** directions guide review & PRs; each ship still needs APPROVE.

---

## North star

A **personal, offline-first** ledger that answers:

> “What did this **session** / **turn** cost me in tokens and dollars?”

…for **Codex first**, then honest ChatGPT surfaces, without lying about Plus vs API billing.

---

## Non-negotiables (laws)

| Law | Meaning |
|-----|---------|
| Local-first | Default path never uploads usage to a third party |
| Dual ledger | Rate-card / API-equivalent $ ≠ ChatGPT seat invoice |
| Privacy | No full prompts by default; never ingest `auth.json` |
| Honest gaps | Unpriced / unknown → GAP, never fake $0 |
| Small ships | Prefer vertical slices over platform rewrites |
| Scope fence v1 | ChatGPT + Codex only (other vendors later, explicit expand) |

---

## Direction tracks (D1–D8)

### D1 — Codex MAXres excellence (core)
**Why:** Station / most power users already have local turn tokens.  
**Outcomes:**
- Robust `token_count` parse across Codex versions  
- Better model discovery (fewer `unknown`)  
- Session titles, parent/subagent rollups without double-count traps  
- Fast re-ingest + optional “since last run”  
**Done looks like:** Re-install on a clean machine → ingest → dashboard useful in &lt;5 minutes.

### D2 — Honest ChatGPT lane
**Why:** Users say “ChatGPT” but Plus has no official per-prompt token invoice.  
**Outcomes:**
- Subscription amortization row (seat $ / day)  
- Optional data-export + tokenizer **shadow** cost (HYP)  
- UI modes: “API-equivalent” vs “cash out the door”  
**Done looks like:** No one confuses Plus chat with API line items.

### D3 — API / org reconciliation (opt-in)
**Why:** When traffic is API-key metered, Usage/Costs APIs are $ truth at coarser grain.  
**Outcomes:**
- Opt-in Admin key from env only  
- Bucketed events labeled **not** per-prompt  
- Reconciliation view: local sum vs org costs (no silent double-count)  
**Done looks like:** Power users can cross-check the bill without losing MAXres Codex view.

### D4 — Pricing fidelity
**Why:** Models and tiers change; snapshot CSV drifts.  
**Outcomes:**
- Alias map (`codex-auto-review` → base rates)  
- Fast / Batch / long-context bands when usage exposes them  
- Documented refresh process from official pricing pages  
**Done looks like:** &lt;5% of turns unpriced for current Codex models.

### D5 — MAXres UX polish
**Why:** Tired principal needs 10-second path.  
**Outcomes:**
- Real date ranges (Today / 7d / 30d on live data)  
- Export CSV of filtered events  
- Clear banners: estimate vs invoice; plan rail vs API rail  
- LOW RES already seeded — keep improving  
**Done looks like:** Expensive session is obvious without reading docs.

### D6 — Packaging & install (coder → everyone)
**Why:** Clone+venv is fine for v0.1; broader adoption needs friction cut.  
**Outcomes:**
- `pip install ai-usage-cost-tracker` (PyPI)  
- Console entrypoint `ai-usage-cost`  
- One-page install for Windows / macOS / Linux  
**Done looks like:** Non-git users can still run it.

### D7 — Quality & trust (OSS)
**Why:** Public repo must stay safe and green.  
**Outcomes:**
- CI green on every PR  
- More fixtures (edge JSONL shapes)  
- SECURITY process tested; no real usage in git  
- CONTRIBUTING clarity for adapters  
**Done looks like:** Strangers can PR adapters without footguns.

### D8 — Explicit non-goals (until a NEW direction)
- Multi-tenant SaaS / hosted “everyone’s data on our server”  
- Auto-scraping ChatGPT web with session cookies  
- Full FinOps for Claude / Gemini / Grok / Cursor in the same v1 fence  
- Tax/accounting certification  

Expand only with Principal `NEW DIRECTION` + finish contract.

---

## Suggested release waves

| Wave | Theme | Tracks |
|------|--------|--------|
| **v0.1.x** | Hardening Codex + docs | D1, D4, D7 |
| **v0.2** | ChatGPT honest lane | D2, D5 |
| **v0.3** | Opt-in Usage API reconcile | D3 |
| **v0.4** | PyPI + polish | D6, D5 |
| **v1.0** | Stable CLI + dual ledger UX + trusted rates | D1–D7 enough for “boring reliable” |

---

## How Web BUILD should use this

1. Read this file + `REVIEW_ROSTER.md` + product laws.  
2. Propose **implementation items** `I1…In` that **map to a track** (`maps_to: D2`).  
3. Do **not** invent a SaaS pivot or vendor merge without Principal direction.  
4. Prefer P1 items that unlock the next wave over random polish.

Human still: `APPROVE` / `REJECT` / `DEFER` / `APPROVE IMPLEMENT`.
