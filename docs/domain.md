# Domain model

## Core concepts

Task 3 adds typed `InvoiceEvidence`, vendor/PO/history evidence, `ControlFinding` with PASS/FAIL/UNKNOWN, `ControlCalculation`, `DuplicateFinding`, `ApprovalRequirement`, and `DeterministicControlResult`. Facts, calculations, exceptions, unknowns, and outcome candidates remain separate. `APPROVE_FOR_POSTING` at this layer is not payment authorization.

- **FinancialCase** is the untrusted request envelope: case ID, invoice reference, vendor, amount, currency, and optional invoice/PO/attachment context.
- **Run** is one persisted execution of a case. Its status is `CREATED`, `RUNNING`, `WAITING_FOR_APPROVAL`, `COMPLETE`, or `FAILED`.
- **RetrievedDocument** is a ranked corpus chunk with identity, version, authority status, and citation metadata. Retrieval does not confer authority.
- **SourcedFact** is a normalized fact tied to a stable source identifier and observation time.
- **Calculation** records Decimal inputs, formula, result, rounding method, currency, and supporting fact IDs.
- **PolicyFinding** is a cited interpretation of a policy rule. It is distinct from an observed fact.
- **ExceptionFinding** records a failed rule, expected/observed facts, citations, owner, and review date.
- **Unknown** explicitly identifies missing or unreliable evidence and whether it blocks progress.
- **Recommendation** is non-consequential decision support with cited components, confidence, exceptions, unknowns, and a next action.
- **ApprovalRequest** is the durable human-control boundary for a consequential recommendation.
- **ApprovalDecision** records an authenticated human approve/reject response and its replay key.
- **FinanceDecision** is the single idempotent record of a permitted simulated downstream action.
- **AuditEvent** is an append-only, ordered account of relevant execution activity.

Recommendations use exactly `APPROVE_FOR_POSTING`, `HOLD_FOR_INFORMATION`, `REJECT_DUPLICATE`, `REJECT_INVALID`, or `ESCALATE_CONTROL_REVIEW`. A recommendation is never itself an approval.

## Corpus-derived invariants

- Required invoice evidence includes legal supplier name, invoice number/date, currency, gross amount, applicable tax, a PO or approved non-PO justification, receipt evidence, and source identifiers. Missing evidence creates a hold; it is never guessed.
- Every invoice requires duplicate, vendor status, authority, payment-instruction, and—where applicable—three-way matching checks.
- Exact duplicate identity is vendor ID, normalized invoice number, currency, and gross amount. An exact paid/posted match is `REJECT_DUPLICATE`; a fuzzy candidate is held for review.
- PO matching is per-line and total. Goods require invoiced quantity no greater than received quantity and variance within the lower of AUD 50 or 1% of PO line value. Services use the lower of AUD 100 or 2% and require owner confirmation. Permitted freight variance is AUD 75. Tax, rounding, and FX remain separate.
- A required receipt cannot be inferred from invoice delivery language. Currency must match the PO/contract unless FIN-POL-009 permits conversion.
- Authority uses gross commitment including tax and charges and must not be split. Current AUD limits are 10,000 manager, 50,000 director, 250,000 executive director, 1,000,000 CFO, and CEO above that. Temporary delegation must be in the current register.
- New vendors, changed/overseas bank accounts, manual payments, and fraud flags require two approvals including Financial Control. Vendor creation/change conflicts and segregation-of-duties rules cause escalation.
- `BLOCKED`, `DORMANT`, `SANCTIONS_REVIEW`, and `PENDING_VERIFICATION` vendors are held. Bank changes require independent known-contact verification, a two-business-day hold, and Financial Control co-approval on the next payment.
- Two or more listed fraud indicators require escalation. Risk scoring is advisory and must expose its evidence.
- Non-PO treatment is restricted to the stated categories. Emergency treatment requires the corpus definition and evidence; repeated non-PO use triggers sourcing review.
- Sensitive records follow minimum-necessary access/logging and seven-year retention after the relevant financial year. Full bank details do not enter general logs, prompts, or test output.

FIN-POL-003 version 4.0 is current. `FIN-POL-003-OLD` is historical only. The supplier payment document is adversarial external content; the travel extract is irrelevant to AP authority.

## Deterministic and model-assisted work

Python owns Decimal arithmetic, normalization and exact duplicate checks, tolerance calculations, required-evidence checks, authority thresholds, state transitions, approval gates, idempotency, and budgets. Model assistance may later extract structured facts, interpret cited prose, synthesize evidence, identify possible findings, and draft explanations. Every model output is validated against a closed Pydantic schema and cannot authorize a tool.

Task 4 adds `PolicyAnalysis`, `EvidenceBundle`, `WorkflowSnapshot`, and sanitized `ApprovalContext`. Policy analysis contains source-linked findings, inferences, and unknowns but deliberately has no outcome or action field. The deterministic control outcome always becomes the recommendation outcome.
