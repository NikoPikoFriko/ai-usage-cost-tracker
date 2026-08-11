# Contributing

Thanks for helping. This repo has **two tracks** — read [docs/TRACKS.md](docs/TRACKS.md) first.

| Track | Branch | Who |
|-------|--------|-----|
| **Universal** | `master` | Everyone — clone, use, PR here |
| **Personal** | `personal` | Maintainer’s station only — not for community PRs |

## You want to add support for *your* AI (Claude, Grok, …)

That is the main contribution path.

1. Fork → branch from **`master`**.  
2. Follow [docs/PROVIDERS.md](docs/PROVIDERS.md) (provider pack).  
3. Implement adapter + docs + anonymized fixture + test.  
4. Open a **Pull Request into `master`**.  
5. Wait for review (honesty + privacy + schema).  

Use PR title: `provider(<id>): <what it ingests>`.

Issue template: **Provider pack (new AI / agent)**.

## Dev setup

```bash
git clone https://github.com/NikoPikoFriko/ai-usage-cost-tracker.git
cd ai-usage-cost-tracker
python -m venv .venv
# activate
pip install -r requirements.txt
pytest -q
python -m src.cli ingest list
```

## Coding guidelines

- **Local-first** — no cloud in the default path without an explicit opt-in flag.  
- **N-way ledger** — set `grain` + `money_rail`; never fake a single invoice.  
- **Privacy** — no full prompts; no secrets; no live usage DB in git.  
- **Tests** — fixture-backed.  
- **Small PRs** — one provider per PR when possible.  

## What we will reject

- Cookie-scraping as the only ingest story  
- Hard-coded personal absolute paths as required defaults  
- PRs that target the `personal` track or dump private session files  
- Collapsing all providers into one unlabeled “total spend”  

## Maintainer: personal track

```bash
git checkout personal
# work under personal/ and experimental adapters
# promote clean pieces to master via PR
```

See `personal/README.md`.
