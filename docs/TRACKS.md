# Two tracks, one direction

This project develops on **two parallel tracks** that share the same architecture (multi-provider plane, N-way ledger, local-first). They must **not** be mixed casually.

```text
                    ┌─────────────────────────────────────┐
                    │  Direction (D9 spend plane)         │
                    │  SCHEMA · ADAPTER_PROTOCOL · UI     │
                    └─────────────────┬───────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
   ┌─────────────────────┐                         ┌─────────────────────┐
   │  UNIVERSAL track    │                         │  PERSONAL track     │
   │  branch: master     │                         │  branch: personal   │
   │  for everyone       │                         │  for you / station  │
   └─────────────────────┘                         └─────────────────────┘
```

## UNIVERSAL (`master`)

**Purpose:** Code and docs that any user can clone and use without your disk layout, emails, or seat prices.

| Include | Exclude |
|---------|---------|
| Adapters with public docs | Hard-coded `D:\…` station paths |
| Anonymized fixtures | Real `tracker.db` / live `data.json` |
| Generic CLI flags | Your real monthly Pro $ as defaults |
| Provider packs from the community | Secrets, cookies, API keys |

**How others contribute:** fork → branch → PR into **`master`** (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

**Default remote branch for OSS:** `master`.

---

## PERSONAL (`personal`)

**Purpose:** Your station-specific evolution — same protocol, your paths, experiments, private adapters.

| Include | Exclude from public history if possible |
|---------|----------------------------------------|
| `personal/` overrides | API keys, `auth.json`, cookies |
| Station scripts, default periods | Unredacted session dumps |
| Experimental adapters (e.g. Grok early) | Anything you would not paste in a public issue |

**Branch:** `personal` (local or private fork recommended if it holds sensitive paths).

**Flow:**

1. Invent / break things on `personal`.  
2. When a piece is **generic enough**, extract it into a clean commit and open a PR to **`master`**.  
3. Do **not** merge raw `personal` into `master`.

---

## Same track rules (both branches)

- Local-first, no cloud by default  
- N-way ledger (`grain`, `money_rail`) — no fake single invoice  
- Privacy: no full prompts by default  
- One provider = one adapter + docs, not a core rewrite  

## Day-to-day commands

```bash
# Universal work (public)
git checkout master
git pull

# Personal station work
git checkout personal
# edit personal/* only when possible

# Promote a generic fix to public
git checkout master
git checkout -b feat/from-personal-…
# cherry-pick or re-implement cleanly
# open PR → master
```

## Directory convention

| Path | Track |
|------|--------|
| `src/adapters/*.py` (no `personal/`) | UNIVERSAL |
| `docs/providers/*.md` | UNIVERSAL |
| `tests/fixtures/*` (anonymized) | UNIVERSAL |
| `personal/**` | PERSONAL only (see `personal/README.md`) |
| `data/`, `web/data.json` | Local runtime — never commit |

## GitHub settings (recommended)

1. Default branch: **`master`** (universal).  
2. Protect `master`: PRs + green CI.  
3. Optional: do **not** set `personal` as default; if you push it, treat it as “my lab,” not “the product.”  
4. Community PRs always target **`master`**.
