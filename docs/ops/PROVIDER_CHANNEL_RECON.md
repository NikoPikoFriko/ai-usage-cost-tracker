# Provider data-channel reconnaissance

**Snapshot:** 2026-08-11 (HST)  
**Scope:** OpenAI/ChatGPT/Codex, xAI/Grok, Anthropic/Claude, Google/Gemini, and Perplexity.  
**Rule:** This document identifies channels that a local-first adapter may consume; it does not authorize access to a live account.

The providers expose different evidence grains. API telemetry can support token or daily-bucket records, while consumer subscriptions and downloaded invoices support cash or seat records. These sources must remain separate even when they refer to the same operator.

## Channel matrix

| Provider / surface | Verifiable channel | Honest grain and rail | Repository-safe implementation path | Gap or restriction |
|---|---|---|---|---|
| OpenAI API | Organization Costs endpoint returns paginated daily buckets with monetary amount/currency and optional project, API-key, or line-item grouping.[1] | `bucket` → `api_metered` | I8 spec first; future opt-in adapter uses an environment-provided Admin key and synthetic response fixtures | Bucketed organization data is not a per-session Codex record and must be reconciled rather than summed with local events |
| OpenAI public rate card | Official pricing page publishes token and tool rates.[2] | Derived request/turn → `credits` or `shadow_estimate`, depending on source | Maintain dated rate-card CSV rows and evidence class; reprice explicitly | A public rate-card estimate is not settled cash or a ChatGPT seat invoice |
| ChatGPT consumer | Official settings/Privacy Portal export produces a ZIP containing chat history and account data.[3] | Conversation-derived estimate only → `shadow_estimate` | I7 remains spec-only; a future parser must be opt-in, discard prompt bodies, and use synthetic fixtures | The export is privacy-sensitive and does not establish an official per-prompt Plus invoice |
| Codex local | Existing project adapter reads local rollout JSONL and deliberately avoids `auth.json` | `turn` → `credits` or `api_metered` only when billing identity is explicit | Keep local JSONL as the highest-resolution source; pursue I2 and I12 | Local tokens can model API-equivalent burn but may not equal a seat payment or bank charge |
| xAI API | Official pricing documents per-token, tool, media, storage, batch, and priority rates.[4] | Request/turn when native usage exists → `api_metered` or provider credit rail | Dated xAI rate rows may be added only with model/tier fields captured from a documented response | Pricing alone is not an account usage feed |
| xAI billing | Official Console docs expose Usage Explorer, prepaid credits, monthly invoicing, and downloadable invoices in the billing area.[5] | Console usage → aggregate API evidence; invoices/top-ups → `invoice_line` or `credits` | Prefer a user-exported file or manual invoice entry; never scrape the authenticated console | No public programmatic usage/cost export endpoint was found in the reviewed official docs |
| Grok consumer/local | Proposed `updates.jsonl` source for IU4 | Source-dependent; do not assign rail until token/cost semantics are documented | Require a redacted schema sample, then commit only a fully synthetic fixture | Official reviewed sources do not document the local file contract; label IU4 `needs-info` if fields cannot be grounded |
| Anthropic API | Usage & Cost Admin API provides organization usage buckets and daily cost reports; it requires an Admin API key and is unavailable to individual accounts.[6] | `1m`/`1h`/`1d` usage buckets and daily cost → `api_metered` | Future opt-in provider pack with environment credentials, pagination, and synthetic fixtures | Priority-tier cost is not included in the documented cost endpoint; usage and cost may require separate reconciliation |
| Claude consumer/team | Official exports include conversation and user data; availability depends on account/organization role.[7] | Conversation export → no default money truth | Treat as privacy-sensitive and spec-only unless a narrow aggregate contract is approved | Conversation data is not a billing export and must not be treated as per-prompt invoice evidence |
| Gemini API / AI Studio | Official billing guide exposes AI Studio usage monitoring and distinguishes prepaid from postpaid billing.[8] | Dashboard aggregate → API usage; purchased credit → `credits`; postpay evidence → cash only when invoiced | Keep current manual Gemini lane; add documented export parsing only when a stable format exists | Dashboard visibility is not itself a stable public API contract |
| Google Cloud Billing | Standard, detailed, FOCUS, and pricing exports can include cost, usage, credits, adjustments, currency, project, SKU, and invoice fields in BigQuery.[9] | Billing rows → `api_metered` or `invoice_line`, depending on export field | Local-first path: user exports a bounded CSV/JSON and imports it locally; live BigQuery access remains opt-in | Export schema can change; adapter needs a normalization layer and must avoid attributing all Google Workspace cash to Gemini |
| Perplexity API | Official API Portal shows token/request usage metrics, per-model rates/costs, credit balance, and invoice history.[10] | Portal aggregate → API usage/credits; invoice → `invoice_line` | Continue manual CSV/subscription lane; add a parser only for a documented downloaded format | Reviewed official docs do not describe a public usage-export API |
| Perplexity Pro | Official help documents downloading subscription invoices from Invoice History.[11] | `subscription_period` → `subscription`; downloaded invoice → `invoice_line` | Manual local invoice import with idempotent synthetic fixtures | A Pro seat is not API token billing; mobile-store invoices are separate cash sources |

## Near-term product decisions

| Priority | Decision | Reason |
|---|---|---|
| 1 | Keep Codex local JSONL as the high-resolution reference lane | It is already implemented, tested, and local-first |
| 2 | Ship ChatGPT manual subscription/invoice only after I6 terminology approval | It adds truthful cash/seat evidence without fabricating per-prompt tokens |
| 3 | Hold IU4 at `needs-info` until the Grok local schema is evidenced | The official sources reviewed establish rates and console billing, not `updates.jsonl` semantics |
| 4 | Keep OpenAI and Anthropic organization APIs as opt-in aggregate adapters | They require privileged keys and produce bucketed data that must be reconciled |
| 5 | Treat Google Cloud Billing export as a separate, broader cloud-billing lane | A Google charge may bundle non-AI services; SKU/service mapping is required |
| 6 | Keep Perplexity on manual subscription/CSV input until an official stable export/API contract is documented | The current repository already supports the honest, low-risk path |

## Fixture and credential policy

Public tests may contain only generated identifiers, fabricated amounts, and model names copied from public documentation. Admin/API credentials must be provided at runtime through environment variables and must never be persisted to SQLite, logs, screenshots, fixtures, or Git. Consumer export ZIPs, console downloads, invoices, and local session paths must remain outside the repository.

## References

[1]: https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage/methods/costs/ "OpenAI API Reference — Organization Costs"
[2]: https://developers.openai.com/api/docs/pricing "OpenAI API — Pricing"
[3]: https://help.openai.com/en/articles/7260999-exporting-your-chatgpt-history-and-data "OpenAI Help — Exporting ChatGPT history and data"
[4]: https://docs.x.ai/developers/pricing "xAI Docs — Pricing"
[5]: https://docs.x.ai/console/billing "xAI Docs — Manage Billing"
[6]: https://platform.claude.com/docs/en/manage-claude/usage-cost-api "Anthropic — Usage and Cost API"
[7]: https://support.claude.com/en/articles/13346720-export-your-organization-s-data "Claude Help — Export organization data"
[8]: https://ai.google.dev/gemini-api/docs/billing "Google AI for Developers — Gemini API Billing"
[9]: https://docs.cloud.google.com/billing/docs/how-to/export-data-bigquery "Google Cloud — Export Cloud Billing data to BigQuery"
[10]: https://docs.perplexity.ai/docs/getting-started/api-groups "Perplexity Docs — API Groups & Billing"
[11]: https://www.perplexity.ai/help-center/en/articles/10353002-billing-faq-for-pro-plan-subscribers.html "Perplexity Help — Billing FAQ for Pro subscribers"
