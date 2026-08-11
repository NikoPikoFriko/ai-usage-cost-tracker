# Publish checklist (Path A — open source)

Owner steps after the open-source roster is committed.

## 1. Create GitHub repo

1. https://github.com/new  
2. Name: `ai-usage-cost-tracker` (or your choice)  
3. **Public**  
4. **No** README/license (repo already has them)  
5. Create

## 2. Replace OWNER placeholders

Search-replace `OWNER` in:

- `README.md` (clone URL + badge)
- `CHANGELOG.md` (compare links)
- `pyproject.toml` (`project.urls`)

Use your GitHub username or org.

## 3. Push

```bash
cd /path/to/ai-usage-cost-tracker
git remote add origin https://github.com/NikoPikoFriko/ai-usage-cost-tracker.git
git branch -M main   # optional if you prefer main
git push -u origin master   # or main
```

## 4. Tag v0.1.0

```bash
git tag -a v0.1.0 -m "v0.1.0 Codex local MAXres cost tracker"
git push origin v0.1.0
```

GitHub → Releases → “Generate release notes” from tag.

## 5. Repo settings (nice)

- About: “Local-first OpenAI Codex token → USD cost tracker”
- Topics: `openai` `codex` `cost-tracking` `tokens` `local-first` `python`
- Enable Issues
- Confirm Actions run green on first push

## 6. Announce (optional)

- Short post: what it does / what it does **not** (Plus ≠ per-prompt $)
- Link to README honest limits

## Do not publish

- `data/tracker.db`
- `web/data.json` with real sessions
- Any real rollout JSONL

