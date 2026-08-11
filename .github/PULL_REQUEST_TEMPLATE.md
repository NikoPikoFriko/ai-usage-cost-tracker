## Track

- [ ] **UNIVERSAL** → targets `master` (for everyone)
- [ ] **PERSONAL** → do not open this kind of PR to public `master` (keep on `personal` branch / private fork)

## Type

- [ ] Provider pack (`provider(...)`)
- [ ] Core / schema / UI
- [ ] Docs only
- [ ] Fix

## Provider pack (if applicable)

- **product id:**
- **cli id:**
- **grain:**
- **money_rail:**
- **docs path:** `docs/providers/…`

## Honesty check

- [ ] Grain is not faked (no “fake turns” from a monthly total)
- [ ] Money rail labeled correctly
- [ ] No secrets / live DB / full prompts in the diff

## Test plan

- [ ] `pytest -q`
- [ ] Manual: `python -m src.cli ingest …` (describe)

## Related

Closes #
