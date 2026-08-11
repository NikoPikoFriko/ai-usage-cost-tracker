# Contributing

Thanks for helping make this useful for more people.

## Dev setup

```bash
git clone <your-fork>
cd ai-usage-cost-tracker
python -m venv .venv
# activate venv
pip install -r requirements.txt
pytest -q
```

## Coding guidelines

- **Local-first** — no cloud calls in the default path without an explicit flag.
- **Privacy** — never store full prompt bodies by default; never commit real session dumps.
- **Honest $** — dual-ledger mindset: rate-card estimate ≠ subscription invoice. Label gaps.
- **Tests** — add or extend pytest for parsers and `cost.py` when you change behavior.
- **Small PRs** — one concern per PR when possible.

## Suggested contribution areas

| Area | Ideas |
|------|--------|
| Adapters | ChatGPT export, Usage API (opt-in), other local agents |
| Pricing | Model aliases, long-context / Fast tiers, refresh script from public docs |
| UI | Date range filters, charts, export CSV |
| Packaging | PyPI entry point, Homebrew formula later |
| Docs | Screenshots, non-English README |

## PR checklist

- [ ] `pytest -q` passes  
- [ ] No secrets / real usage DB in the diff  
- [ ] README or CHANGELOG updated if user-facing  
- [ ] New models documented if pricing rows added  

## Code of conduct

Be respectful. No harassment. Assume good intent; prefer clear technical feedback.
