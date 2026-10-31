# Cash-trail cross-reference

**Status:** Implemented local-only contract. Public fixtures are entirely synthetic.

Invoice lines, bank settlements, subscription commitments, and token-cost estimates
are separate evidence. Import each invoice and bank row as its own `UsageEvent`;
links preserve provenance and never delete or rewrite evidence.

## Event rules

| Field | Invoice / bank rule |
|---|---|
| `source_surface` | `provider_invoice` / `bank_statement` |
| `money_rail` | Always `invoice_line` |
| `grain` | `day` |
| Token fields | Null |
| `amount_native`, `currency` | Preserve original signed amount and 3-letter currency |
| `cost_usd` | Set only when the source currency is USD; no implicit FX |
| `cash_status` | Invoice: `posted`; bank: `posted` or `pending` |
| `raw_ref` | Local source path and source-record locator; do not publish |

Debits are positive expenses and bank credits/refunds are negative. Invoice credit
notes are negative. Pending authorizations are excluded from posted-cash ranges
and reported separately. Native-currency amounts are never combined across
currencies.

## Links and matching

`cash_cross_references` stores `settles`, `refunds`, `partial_settlement`, or
`candidate_match` relationships with `candidate`, `confirmed`, or `rejected`
status. Confirmations require `operator` or an explicit `rule:<id>`. Updates are
recorded in append-only `cash_link_history`.

The importer may create a fuzzy `candidate_match`, but never confirms it.
Operator-confirmed full settlements count the posted bank row once and retain
the invoice as supporting evidence. Partial settlements count posted bank rows
and show the remaining invoice amount separately. Rejected links do not collapse
either record.

## Dashboard interpretation

Cash ranges are grouped by currency. The lower bound is posted bank evidence;
the upper bound includes unresolved invoice amounts and confirmed partial
settlement remainders. Pending bank rows are shown separately. The range is an
uncertainty view, not a balance or payment-status assertion. Subscription,
credits, API-metered, rate-card, and shadow-estimate rails remain separate.

Event identity is a deterministic hash of source channel, evidence type, source
record ID, signed amount, currency, and source date. Re-imports are idempotent.
Corrected amounts/dates produce distinct evidence records rather than silently
overwriting an earlier record.

Use only user-selected local CSV files:

```text
python -m src.cli ingest cash-trail --invoices invoices.csv --bank bank.csv
python -m src.cli ingest cash-trail --links operator-links.csv
```

The importer does not access bank accounts, email, browser profiles, or payment
systems. Tests and committed fixtures must contain synthetic data only.
