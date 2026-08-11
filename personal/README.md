# PERSONAL track (this directory)

**Branch:** `personal`  
**Not for random community PRs.**

Use this folder for **your** station-only config and experiments:

```text
personal/
  README.md                 # this file
  channels.override.example.yaml
  notes.md                  # optional free notes
  # channels.override.yaml  # gitignored if you create it with secrets
```

## What belongs here

- Default monthly seat amounts you actually pay  
- Paths unique to your machine (as **examples in notes**, not as required code defaults)  
- Scratch adapters before they are cleaned for `master`  
- Scripts that call station tools under `D:\PROJECT_CENTER\…`

## What must never be committed (even on personal if the remote is public)

- API keys, cookies, `auth.json`  
- Live `data/tracker.db` full of private sessions  
- Unredacted JSONL dumps  

Prefer a **private fork** if this branch will hold sensitive material.

## Promote to universal

When something works for you **and** would work for a stranger:

1. Strip paths and personal $ amounts.  
2. Add anonymized fixture + docs under `docs/providers/`.  
3. PR → **`master`** with title `provider(...): …`.
