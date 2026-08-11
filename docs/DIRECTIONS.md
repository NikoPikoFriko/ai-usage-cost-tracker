# Developmental directions

**Status:** Principal NEW DIRECTION — multi-provider spend plane (2026-08-11)  
**Product:** Personal AI spend observatory · local-first · open source  
**Not a commitment:** each ship still needs `APPROVE` / `APPROVE IMPLEMENT`

---

## North star

> Make **agent spend observable across the whole AI stack**—at the resolution each platform actually exposes.

Not “track OpenAI better.” A personal, offline-first ledger that answers:

> “Where did my AI money go this week—**by agent**, by session, by model?”

…for **Codex, Grok, Claude, Perplexity, ChatGPT**, and others—without collapsing them into a fake single invoice or a cloud FinOps product on day one.

---

## Architectural axes (orthogonal)

| Axis | Meaning |
|------|---------|
| **Provider adapter** | How usage enters (local logs, export, Usage API, invoice, manual CSV) |
| **Grain** | turn / request / session / day / subscription_period / bucket — **declared, never faked** |
| **Money rail** | `api_metered` · `subscription` · `credits` · `shadow_estimate` · `invoice_line` |
| **Identity** | One human operator, many products (not multi-tenant SaaS by default) |
| **Trust** | Every row: `source_product`, `ingest_channel`, `evidence_class`, `billing_identity`, `grain`, `money_rail` |

**Law (N-way ledger):** never sum apples and oranges into one “total AI spend” without an **explicit rollup mode** (`by_rail` default, `metered_only`, or `all_labeled`).

See [SCHEMA.md](SCHEMA.md) and [ADAPTER_PROTOCOL.md](ADAPTER_PROTOCOL.md).

---

## Non-negotiables

| Law | Meaning |
|-----|---------|
| Local-first | Default path never uploads usage to a third party |
| N-way ledger honesty | Rate-card ≠ subscription ≠ invoice without labels |
| Privacy | No full prompts by default; never ingest `auth.json` |
| Honest gaps | Unpriced / unknown → GAP, never fake $0 |
| Small ships | One adapter / vertical slice per PR when possible |
| Extensibility | New agent = adapter + fence row, not a fork |

---

## Non-goals (until further NEW DIRECTION)

- Hosted multi-user SaaS of everyone’s chats  
- Cookie-scraping private web UIs as primary ingest  
- One unlabeled “true spend” across all vendors  
- Enterprise FinOps before personal multi-agent clarity works offline  

---

## Direction tracks

### D1 — Codex MAXres excellence
Local turn tokens remain the gold path. Harden parse, models, incremental ingest, subagent rollups.

### D2 — Honest ChatGPT lane
Seat amortization (`subscription`) + optional shadow tokens (`shadow_estimate`). Never fake Plus as API.

### D3 — API / org reconciliation (opt-in)
Usage/Costs APIs as `bucket` grain + `api_metered` or `invoice_line`. Cross-check only; no silent double-count.

### D4 — Pricing fidelity
Aliases, Fast/long-context tiers, multi-family rate cards, refresh from official docs.

### D5 — MAXres UX polish
Date filters, export CSV, estimate vs cash banners, **provider filter**, **by_rail totals**.

### D6 — Packaging & install
PyPI, entrypoint `ai-usage-cost`, low-friction install.

### D7 — Quality & trust (OSS)
CI, fixtures, safe contrib path, no live usage in git.

### D8 — Explicit historical non-goals
Still: no SaaS / cookie primary / unlabeled mega-total. Multi-vendor is now **in** via D9—not a free-for-all rewrite.

### D9 — Multi-provider personal spend plane (**axis**)
**Why:** Real money burns on Grok, Claude, Perplexity, etc., off the board.  
**Outcomes:**
- Open `source_product` set  
- Declared `grain` + `money_rail` on every row  
- Adapter registry protocol  
- UI filter by provider; totals by rail  
- Waves U1 Grok → U2 Claude → U3 Perplexity → U4 community packs  

**Done looks like:** Adding a provider is docs + adapter + map, not a fork; weekly “where did money go” works offline.

---

## Provider waves

| Phase | Surfaces | Resolution target |
|-------|----------|-------------------|
| v0.1 | Codex local | Turn MAXres |
| Next | ChatGPT honest | Seat + optional shadow |
| **U1** | Grok local sessions / cost ticks | Turn or session |
| **U2** | Claude / Anthropic | API or export |
| **U3** | Perplexity | Subscription + export if any |
| **U4** | Adapter registry packs | Community |

---

## Suggested release waves

| Wave | Theme | Tracks |
|------|--------|--------|
| v0.1.x | Schema rails + Codex tagged + UI by_rail | D9, D1, D5 |
| v0.2 | Grok U1 + ChatGPT seat | D9, U1, D2 |
| v0.3 | Claude + opt-in Usage API | U2, D3 |
| v0.4 | Perplexity + PyPI | U3, D6 |
| v1.0 | Stable multi-agent observatory | D1–D9 enough for “boring reliable” |

---

## How Web BUILD / implementers use this

1. Map every **I\*** / **IU\*** to a D-track (prefer D9 for plane work).  
2. Do not invent SaaS or cookie-scrape primary.  
3. Prefer serial adapters over multi-vendor mega-PRs.  
4. Human: `APPROVE` / `REJECT` / `DEFER` / `APPROVE IMPLEMENT`.
