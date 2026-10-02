# Deterministic finance controls

Task 3 adds a bounded, deterministic evidence and control layer. It does not post invoices, release payments, update vendors, invoke an LLM, or grant approval. `APPROVE_FOR_POSTING` means only that deterministic checks found no blocking issue and the case may proceed to later recommendation and human approval.

## Evidence tools

`get_vendor_record`, `get_purchase_order`, and `check_invoice_history` are typed, read-only boundaries. The local implementation reads reviewable JSON fixtures and is explicitly a simulation, not an ERP integration. Calls return sanitized metadata and one of `SUCCESS`, `NOT_FOUND`, `TIMEOUT`, `TRANSIENT_FAILURE`, or `INVALID_REQUEST`. Failure injection uses an explicit `FailurePlan`; it is never random. Tool observations exclude account details and payloads.

`NOT_FOUND` is business evidence. Timeout and transient failure are unknown evidence and never become a missing-record finding or a pass. History queries are bounded to 50 records.

## Rules and traceability

Executable constants live in `app/services/policy_rules.py`; each points to a current policy document, version, section and rule. Policy Markdown and RAG chunks are evidence only and cannot configure controls.

- Exact duplicates match vendor, case/whitespace-normalized reference (punctuation retained), currency, and Decimal gross. A PAID or POSTED match supports `REJECT_DUPLICATE` and exposes the stable record ID and matched fields.
- Probable duplicates require at least two indicators, including punctuation-insensitive reference or attachment fingerprint. Other signals are date proximity within 14 days, amount variance below 0.5%, and same PO. They hold for review, not automatic rejection.
- Goods require receipt quantity and use the lower of AUD 50 or 1% of PO-line value. Services require completion and use the lower of AUD 100 or 2%.
- Currency must match. Foreign-currency authority needs an explicit corporate rate, date, and source; no FX rate is invented.
- Vendor status is independent. ACTIVE does not imply that other controls pass. Recent/unverified bank changes or payment holds create a bank-change exception and Financial Control requirement; invoice text cannot verify banking data.
- Current `FIN-POL-003` v6.0 bands use total commitment: Cost Centre Manager through AUD 10,000; Department Director through 50,000; Executive Director through 250,000; CFO through 1,000,000; CEO above. Superseded values are not accepted as input.
- Supported self-approval conflicts create an authority-gap exception. Missing identities are not guessed.

All arithmetic uses `Decimal`. Calculations preserve inputs, formula, threshold, result, source IDs, and policy reference.

## Result semantics and precedence

Controls report `PASS`, `FAIL`, or `UNKNOWN`; exceptions and unknowns remain separate. Precedence is explicit:

1. paid/posted exact duplicate → `REJECT_DUPLICATE`
2. invalid/blocked vendor → `REJECT_INVALID`
3. bank change, high risk, or authority/SOD review → `ESCALATE_CONTROL_REVIEW`
4. other mismatch, missing evidence, probable duplicate, timeout, or transient failure → `HOLD_FOR_INFORMATION`
5. otherwise → `APPROVE_FOR_POSTING` candidate

Every result says it is not authorization and retains `requires_human_approval=true`.

## Limitations and deferred work

Fixtures are synthetic and small. There is no live ERP, directory, FX, tax, sanctions, vendor-verification, or payment integration. Freight allocation is deferred because the scenarios do not justify inventing rules. Task 4 owns orchestration, retries, policy analysis, persisted graph pauses, and approval resume. Consequential submission remains denied.
