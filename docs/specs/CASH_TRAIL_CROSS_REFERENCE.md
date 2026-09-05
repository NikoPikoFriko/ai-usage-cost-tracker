# Cash-trail cross-reference specification

**Status:** Proposed v0.2 contract; documentation and synthetic fixtures only.  
**Applies to:** local invoice, receipt, and bank-statement imports.  
**Does not authorize:** account access, bank login, payment actions, or ingestion of real financial records into Git.

## Purpose

Token usage, subscription commitments, provider invoices, and bank settlement are different evidence. The tracker must preserve each source while preventing one purchase from appearing twice in a default cash view.

> **Store evidence separately; link it explicitly; collapse it only after the relationship is confirmed.**

## Event representation

Each imported invoice or bank row becomes its own `UsageEvent`. This retains source provenance and permits re-import without mutating another provider's record.

| Field | Invoice example | Bank example | Rule |
|---|---|---|---|
| `source_product` | `synthetic_ai` | `synthetic_ai` or `unknown_ai` | Open provider string; mapping may remain uncertain |
| `source_surface` | `provider_invoice` | `bank_statement` | Identifies the evidence surface |
| `grain` | `day` | `day` | Current schema-compatible grain; the source record itself remains one event |
| `money_rail` | `invoice_line` | `invoice_line` | Cash evidence rail; never `api_metered`, `credits`, or `shadow_estimate` |
| token fields | `null` | `null` | Cash evidence does not invent tokens |
| `cost_usd` | Invoice total when currency is USD | Posted amount when currency is USD | Signed amount; refunds are negative |
| `evidence_class` | `OBS` for an original provider invoice | `OBS` for a posted statement row; `CAND` while pending | Evidence quality does not prove cross-source identity |
| `raw_ref` | Local file plus source-record locator | Local file plus row locator | Local only; never publish real paths |

A production implementation should add `amount_native` and `currency` before supporting non-USD imports. `cost_usd` may be populated from another currency only when the record contains explicit conversion metadata; otherwise preserve native currency and leave USD conversion unset. Never apply silent FX conversion.

## Cross-reference table

Do not overload `parent_event_id`, which describes an event graph rather than financial evidence. Add a dedicated local table when this spec is implemented:

| Column | Meaning |
|---|---|
| `link_id` | Stable hash of the ordered evidence IDs and relationship |
| `invoice_event_id` | Invoice/receipt event |
| `settlement_event_id` | Posted or pending bank event |
| `relation` | `settles`, `refunds`, `partial_settlement`, or `candidate_match` |
| `status` | `candidate`, `confirmed`, or `rejected` |
| `confidence` | Numeric or enumerated matching confidence; never a substitute for status |
| `matched_on` | Auditable signals such as amount, currency, date window, normalized merchant |
| `confirmed_by` | `operator` or a future explicit rule identifier |
| `created_at` / `updated_at` | Local audit timestamps |

A matching process may propose a `candidate` link from amount, currency, merchant family, and a bounded date window. It must never promote that link to `confirmed` solely through fuzzy matching.

## Cash precedence and rollup

| Situation | Default cash treatment |
|---|---|
| Confirmed bank settlement linked to an invoice | Count the posted bank event once; show the invoice as supporting evidence |
| Confirmed invoice with no bank evidence in the selected window | Count the invoice once and label it **invoiced, settlement not observed** |
| Pending bank authorization | Exclude from settled cash; show separately as pending |
| Candidate invoice↔bank match | Do not silently collapse. Show a duplicate-risk warning and a lower/upper cash range |
| Confirmed partial settlements | Count posted settlement events; retain the unpaid invoice remainder as unresolved |
| Refund linked to original evidence | Count the signed bank refund once and retain the provider credit note as supporting evidence |
| Subscription schedule plus invoice or bank evidence | The scheduled seat remains `subscription`; cash evidence remains `invoice_line`; do not add them into one unlabeled total |
| Rate-card or shadow event plus cash evidence | Keep analytical and cash rails separate; cross-reference may explain the relationship but never changes either value |

**Source precedence after a confirmed link:** posted bank settlement → provider invoice/credit note → receipt/email claim → manually scheduled subscription. This precedence selects the cash representative; it does not delete lower-precedence evidence.

When duplicate candidates remain unresolved, the UI must not present a single precise cash figure. It should display a lower bound based on posted/confirmed cash and an upper bound that includes unresolved invoice candidates, grouped by currency.

## Deterministic identity

The importer should derive each event ID from the ingest channel, a normalized source-record ID, signed amount, currency, and source date. Re-importing identical evidence is idempotent. Corrections create a new signed correction/refund event or replace a row only when the provider supplies a stable mutable record ID; the original audit relationship remains visible.

## Synthetic fixture contract

The repository may include only obviously synthetic invoice, bank, and link rows. Fixture descriptors must use fictitious merchants and identifiers; amounts must not mirror a user's live plan; paths, names, account suffixes, invoice numbers, and transaction IDs must be fabricated.

The companion fixtures demonstrate one confirmed USD match and one unresolved invoice candidate:

| Fixture | Purpose |
|---|---|
| `tests/fixtures/cash_trail_invoice_sample.csv` | Two fictitious provider invoices |
| `tests/fixtures/cash_trail_bank_sample.csv` | One posted settlement matching the first invoice |
| `tests/fixtures/cash_trail_links_sample.csv` | One operator-confirmed `settles` link |

## Acceptance criteria for a future implementation

- [ ] Invoice and bank records are persisted as separate, idempotent events.
- [ ] Token fields remain null for all cash evidence.
- [ ] Cross-source links use a dedicated table and auditable status.
- [ ] Fuzzy matching creates candidates only.
- [ ] Confirmed matches count the posted bank settlement once in default cash totals.
- [ ] Unresolved duplicate candidates produce a lower/upper range, not a false precise total.
- [ ] Pending authorizations, refunds, partial settlements, and multi-currency gaps remain explicit.
- [ ] Subscription, cash, rate-card, credit, and shadow rails remain separately labeled.
- [ ] No real statement, invoice, billing identity, prompt, secret, or local path is committed.
