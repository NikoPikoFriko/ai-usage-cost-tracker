# Issue and Pull Request Staleness Policy

**Status:** Proposed operating policy  
**Repository:** [`NikoPikoFriko/ai-usage-cost-tracker`](https://github.com/NikoPikoFriko/ai-usage-cost-tracker)  
**Snapshot:** `master` at `8c185dd71bc974dfbcda0e3b440bc44e0e56257a` on 2026-08-11 (HST)

This policy keeps the queue reviewable without converting inactivity into an automatic rejection. The repository is small, public, and maintainer-led, so automation should **label and prompt**, while closure remains a human decision.

## Operational definitions

| Object | Inactive threshold | Stale action | Human closure rule |
|---|---:|---|---|
| Issue | 30 days without a human-authored update | Apply `stale` and ask for current scope, reproduction evidence, or an implementation owner | A maintainer may close only after a further 14 days with no substantive reply |
| Pull request | 14 days without a human-authored update | Apply `stale` and request rebase/CI/decision status | Do not auto-close; a maintainer reviews CI, conflicts, and author response |
| `needs-info` issue | 14 days after the information request | Keep `needs-info`; optionally add `stale` | A maintainer may close after confirming that acceptance criteria cannot be evaluated |
| Draft PR | No automatic stale processing | Review manually when it blocks a release or roadmap item | Never close solely because it is a draft |

> **Stale is a queue signal, not a quality judgment.** New evidence, a clarifying comment, a rebase, or renewed ownership removes the stale state.

An **abandoned PR** is an open PR that meets all of these conditions: it has been inactive for more than 14 days; required CI is failing or the branch conflicts with `master`; a maintainer has requested action; and the author has not responded within seven additional days. A stale but green and mergeable PR is not abandoned.

## Human work versus bot noise

Human-authored scope changes, review responses, commits, and evidence reset the review clock. Dependabot-style updates, workflow status messages, and automated stale comments are **bot noise** for the manual policy and do not demonstrate renewed ownership. The standard stale action uses GitHub's `updated_at` field, so maintainers must still inspect bot-heavy threads before closing anything.[1]

## Label set

| Label | Action | Suggested color | Meaning |
|---|---|---|---|
| `stale` | Create | `BFDADC` | Inactive beyond the policy threshold; requires a maintainer or author decision |
| `needs-info` | Create | `D4C5F9` | Acceptance criteria, reproduction evidence, source format, or ownership is missing |
| `good first issue` | Keep existing | `7057FF` | Small, bounded task suitable for a new contributor |
| `provider-pack` | Create | `0E8A16` | Provider adapter, fixture, documentation, or channel registration work |
| `cash-trail` | Create | `5319E7` | Bank, invoice, receipt, or cross-reference design; no live financial data in public fixtures |

GitHub already provides the special label **`good first issue`**. Do not create a duplicate hyphenated `good-first-issue` label.

## Responsible collaborator

The repository currently has one collaborator with triage and administration permissions: [`@NikoPikoFriko`](https://github.com/NikoPikoFriko). Until another collaborator is explicitly added, assign roadmap Issues and final stale/closure decisions to `@NikoPikoFriko`. Community contributors may own implementation through a linked PR without receiving repository administration rights.

## Automation options

| Approach | Tradeoffs | Cost | Setup complexity |
|---|---|---|---|
| Manual monthly review | Maximum judgment; no automated comments; easiest to ignore during busy periods | No additional automation usage | Low |
| Weekly label-only workflow | Consistent 30-day Issue and 14-day PR prompts; requires maintainers to distinguish bot noise and make every closure decision | Uses ordinary GitHub Actions minutes and API operations | Low–medium |

**Recommendation:** use the weekly, label-only workflow in `.github/workflows/stale.yml`; never auto-close PRs or Issues in the initial configuration. GitHub documents that `actions/stale` can label/comment on inactive items and supports separate Issue/PR thresholds, exemptions, and `-1` to disable automatic closure.[1] [2]

## One-time application to the current repository

| Check | Finding | Owner | Next step |
|---|---|---|---|
| All GitHub Issues | **0 total** | `@NikoPikoFriko` | Seed the verified residual roadmap as separate Issues |
| Open pull requests | **0** | `@NikoPikoFriko` | No stale or abandoned PR action required |
| Historical pull requests | **11 total; 11 merged** | `@NikoPikoFriko` | Retain as implementation history; no hygiene action |
| Inactive Issues (>30 days) | **0** | `@NikoPikoFriko` | No labels or comments to apply |
| Inactive PRs (>14 days) | **0** | `@NikoPikoFriko` | No labels or comments to apply |
| Abandoned PRs | **0** | `@NikoPikoFriko` | None |
| Bot-only queue noise | **0 open items** | `@NikoPikoFriko` | Re-evaluate if dependency bots are enabled later |
| Latest `master` CI | **Passing** for `8c185dd` | `@NikoPikoFriko` | Preserve as required check for future PRs |

The empty current queue is a real result, not a skipped audit. The next hygiene risk is the inverse problem: roadmap work exists only in `REVIEW_ROSTER.md`, so it is invisible to GitHub Issue search, assignment, labels, and stale review.

## Maintainer checklist

1. Confirm the item is not exempt because it is security-sensitive, release-blocking, or intentionally deferred.
2. Confirm the last **human** update date.
3. Add `needs-info` before `stale` when the blocker is missing evidence rather than inactivity alone.
4. Never close a PR solely because CI is red; first identify whether the failure is product code, test infrastructure, or a stale base branch.
5. Never paste real session paths, prompts, API keys, `auth.json`, invoices, bank rows, or private billing identities into a public Issue.
6. Link replacements before closing duplicates or superseded roadmap entries.

## References

[1]: https://github.com/actions/stale "actions/stale — official repository and configuration reference"
[2]: https://docs.github.com/actions/managing-issues-and-pull-requests/closing-inactive-issues "GitHub Docs — Closing inactive issues"
