# Requirements traceability

Status meanings: **IMPLEMENTED** is present and verified in this repository; **SIMULATED** exercises
the production-shaped boundary with local fixtures; **PARTIAL** implements only the stated subset;
**NOT_IMPLEMENTED** is absent; **NOT_APPLICABLE** is outside this local assessment architecture.

## Interface and workflow

| Requirement | Implementation evidence | Verification | Status |
| --- | --- | --- | --- |
| Start a run | `POST /runs` creates a persisted run and executes to a terminal or approval boundary. | API/workflow integration tests | IMPLEMENTED |
| Get run status/result | `GET /runs/{run_id}` returns run, typed workflow snapshot, approval, decision, and audit. | API integration tests | IMPLEMENTED |
| Approve or reject | `POST /runs/{run_id}/approval` resolves the pending approval and resumes the same run. | Approval, rejection, replay, restart tests | IMPLEMENTED |
| List evaluations | `GET /evaluations` returns FIN-001–FIN-005 definitions. | Evaluation API tests | IMPLEMENTED |
| Run evaluations | `POST /evaluations/run` runs the deterministic suite. | Evaluation API tests | IMPLEMENTED |
| Explicit state graph | Fixed LangGraph nodes and application-controlled edges in `app/agent/graph.py`. | Graph contract and workflow tests | IMPLEMENTED |
| Bounded execution | Persisted step and tool-call counters fail safely when exceeded. | Budget and workflow tests | IMPLEMENTED |
| No unbounded autonomous loop | The graph has a fixed topology; no ReAct/planner loop exists. | Static topology review and graph tests | IMPLEMENTED |
| Durable approval pause | `WAITING_FOR_APPROVAL` is committed to SQLite and HTTP returns. | Workflow/API and restart tests | IMPLEMENTED |
| Same-run resume | Approval loads the existing run/checkpoint and resumes controlled stages. | Restart/resume integration test | IMPLEMENTED |

## Tools and evidence

| Requirement | Implementation evidence | Verification | Status |
| --- | --- | --- | --- |
| `retrieve_finance_documents` | Typed read-only retrieval boundary over the local index. | RAG contract/integration tests | IMPLEMENTED |
| `get_vendor_record` | Typed fixture-backed adapter with explicit outcomes and timing. | Finance-tool contract tests | SIMULATED |
| `get_purchase_order` | Typed fixture-backed PO/receipt adapter. It returns PO lines, totals, currency, approval, and receipts; policy tolerances deliberately remain application rules rather than fields on the simulated PO response. | Finance-tool and reconciliation tests | PARTIAL |
| `check_invoice_history` | Typed bounded fixture query exposing stable history IDs. | Tool and duplicate tests | SIMULATED |
| `submit_finance_decision` | Deny-by-default adapter verifies persisted approval and records one local decision. | Direct-denial, approval, idempotency tests | SIMULATED |
| Tool timeout | Deterministic failure plan plus bounded retry; remains `UNKNOWN`. | FIN-004 and workflow tests | IMPLEMENTED |
| Transient tool failure | Explicit reproducible failure category and bounded retry. | Tool/workflow tests | IMPLEMENTED |
| Not-found distinct from failure | Tool results preserve business `NOT_FOUND` separately from infrastructure errors. | Tool/control tests | IMPLEMENTED |
| Sanitized tool observability | Audit events contain tool, attempt, outcome, category, and duration without raw payloads. | Redaction and workflow tests | IMPLEMENTED |

## LLM and RAG

| Requirement | Implementation evidence | Verification | Status |
| --- | --- | --- | --- |
| Model abstraction | `ModelProvider` with live OpenAI-compatible and deterministic fake adapters. | Provider/policy-analysis tests | IMPLEMENTED |
| Configuration outside orchestration | Provider, model, base URL, timeout, and retries come from settings/environment. | Configuration review and tests | IMPLEMENTED |
| Live model path | OpenAI-compatible `/chat/completions` adapter with configured model identifier. | Unit tests; live smoke requires credentials | IMPLEMENTED |
| No-key stable tests | Injected fake model uses no network or credentials. | Full deterministic test/evaluation suite | IMPLEMENTED |
| Structured output | `PolicyAnalysis` Pydantic schema separates findings, inferences, unknowns, explanation, and confidence. | Schema and workflow tests | IMPLEMENTED |
| Malformed-output handling | Bounded model retry/repair, then persisted safe failure. | Malformed-once and exhausted-retry tests | IMPLEMENTED |
| Citation validation | Citation IDs must be retrieved; authoritative findings require current-authority chunks. | Policy-analysis and evaluation tests | IMPLEMENTED |
| Markdown/YAML ingestion | Typed front-matter validation with explicit document errors. | Ingestion contract/unit tests | IMPLEMENTED |
| Heading-aware chunking | Section hierarchy and deterministic bounded subchunks. | Chunking tests | IMPLEMENTED |
| Local reproducible index | Versioned deterministic JSON index with corpus fingerprint. | Rebuild and byte-equivalence tests | IMPLEMENTED |
| Hybrid retrieval | Explainable BM25, sparse TF-IDF cosine, and metadata coverage ranking. | RAG evaluation and retrieval tests | IMPLEMENTED |
| Stable citations | Document/version/section/source/chunk identity is independent of ranking score. | Citation-integrity tests | IMPLEMENTED |
| Current/superseded semantics | Superseded evidence remains retrievable and is always historical-only. | Authority retrieval and traceability tests | IMPLEMENTED |
| Adversarial/irrelevant evidence | Supplier and travel documents remain retrievable with non-authority metadata. | Retrieval tests and FIN-003 | IMPLEMENTED |

## Deterministic finance controls

| Requirement | Implementation evidence | Verification | Status |
| --- | --- | --- | --- |
| Decimal monetary arithmetic | Float rejection and `Decimal` calculations throughout contracts/services. | Domain and control tests | IMPLEMENTED |
| Three-way reconciliation | Goods/services line, quantity, receipt/completion, price, total, and currency checks. | Finance-control tests and FIN-001 | IMPLEMENTED |
| Policy tolerances | Reviewed constants with current document/version/section references. | Boundary and corpus-derived traceability tests | IMPLEMENTED |
| Exact duplicate detection | Vendor, normalized reference, currency, gross amount, and paid/posted status. | Duplicate tests and FIN-002 | IMPLEMENTED |
| Probable duplicate handling | Policy-supported indicators cause hold, never automatic rejection. | Probable-duplicate tests | IMPLEMENTED |
| Missing evidence | Explicit exceptions/unknowns block payment-ready outcomes. | Missing PO/receipt and FIN-004 tests | IMPLEMENTED |
| Vendor/bank controls | Status, bank-change, new/overseas vendor, manual-payment, and fraud requirements. | Control and FIN-003 tests | IMPLEMENTED |
| Delegated authority | Current FIN-POL-003 v4.0 bands use gross commitment and reject superseded authority. | Threshold/traceability tests | IMPLEMENTED |
| Deterministic outcome precedence | Explicit duplicate, invalid, escalation, hold, then candidate precedence. | Outcome-precedence tests | IMPLEMENTED |
| Runtime rules protected from RAG | Policy Markdown is never executable configuration. | Architecture review and traceability tests | IMPLEMENTED |

## Approval, persistence, and security

| Requirement | Implementation evidence | Verification | Status |
| --- | --- | --- | --- |
| Human approval gate | A posting candidate persists exactly one pending request before stopping. | Workflow/API tests and FIN-001 | IMPLEMENTED |
| Approver authority validation | Local directory validates active fixture identity, role, and AUD limit. | Approval tests | SIMULATED |
| Rejection path | Rejection completes without a finance decision or submission. | Workflow/API tests | IMPLEMENTED |
| Callback replay | Same key/same payload returns the stable result; conflicts do not alter history. | Integration/API tests and FIN-005 | IMPLEMENTED |
| Submission idempotency | Stable effective-decision key plus unique run/key constraints. | Submission/replay tests | IMPLEMENTED |
| Restart/crash recovery | Typed state reload plus committed approval/decision permits safe replay. | Fresh-service restart test | IMPLEMENTED |
| Append-only audit | Ordered per-run events cover nodes, retrieval, tools, model, approval, and submission. | Persistence/workflow/evaluation tests | IMPLEMENTED |
| Retrieved text cannot authorize | RAG/model have no submit capability; submitter checks persistence. | Architecture review and FIN-003 | IMPLEMENTED |
| Sensitive-data minimization | Redaction plus fixture masking excludes secrets/full bank details/full prompts from audit. | Redaction tests and repository review | IMPLEMENTED |
| Real payment or bank capability | No adapter can move money, post to an ERP, or change bank data. | Static component review | NOT_IMPLEMENTED |

## Results, deliverables, and evaluation

| Requirement | Implementation evidence | Verification | Status |
| --- | --- | --- | --- |
| Sourced facts | `DeterministicControlResult.sourced_facts` and model source-linked findings. | Schema/control/workflow tests | IMPLEMENTED |
| Calculations | Structured formulas, Decimal inputs/results, thresholds, and policy references. | Control tests | IMPLEMENTED |
| Inferences/assumptions | `PolicyAnalysis.inferences` remains distinct from facts. | Policy-analysis tests | IMPLEMENTED |
| Unknowns | Control and model unknowns remain explicit and blocking where required. | Control/workflow tests | IMPLEMENTED |
| Policy findings and citations | Deterministic and model findings retain current-policy traceability. | Traceability/citation tests | IMPLEMENTED |
| Exceptions | Typed policy categories expose expected, observed, evidence, and owner. | Control tests | IMPLEMENTED |
| Actions/next action | Recommendation next action, approval decision, finance decision, and audit events are exposed. | API/evaluation tests | IMPLEMENTED |
| Runnable source and locked setup | Python source, `uv.lock`, `.env.example`, Make, Dockerfile, and Compose. | Clean-room and Docker verification | IMPLEMENTED |
| README and design note | Reviewer quick start plus this repository's 1–2 page engineering rationale. | Documentation audit | IMPLEMENTED |
| Architecture and component manifest | Mermaid diagrams and explicit real/simulated classifications. | Documentation audit | IMPLEMENTED |
| Automated tests | Unit, contract, integration, workflow, and evaluation suites. | `make test` | IMPLEMENTED |
| Successful and exception examples | Generated FIN-001, FIN-002, and FIN-004 sanitized JSON outputs. | `make eval-samples` | IMPLEMENTED |
| FIN-001 valid match | Real workflow pauses, approves, resumes, and records one simulated decision. | `make eval` | IMPLEMENTED |
| FIN-002 exact duplicate | Deterministic paid duplicate rejection with no approval/submission. | `make eval` | IMPLEMENTED |
| FIN-003 prompt injection | ADV-001 remains untrusted evidence and cannot bypass controls/approval. | `make eval` | IMPLEMENTED |
| FIN-004 unavailable PO | Bounded timeout attempts remain unknown and block approval/submission. | `make eval` | IMPLEMENTED |
| FIN-005 duplicate callback | Stable replay produces one effective local submission. | `make eval` | IMPLEMENTED |
| Cloud deployment/cost cleanup | The solution is intentionally local and creates no cloud resources. | Architecture/configuration review | NOT_APPLICABLE |

The **PARTIAL** PO row records a deliberate contract difference: tolerance values are controlled,
policy-traced application constants rather than trusted from a simulated ERP payload. The one
**NOT_IMPLEMENTED** row is a required safety property: this assessment intentionally contains no
real-money or bank-update capability. Simulated rows are explicit external-system boundaries, not
claims of production integration.
