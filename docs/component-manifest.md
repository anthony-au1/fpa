# Component and configuration manifest

| Component | Implementation | Classification | Configuration | Trust boundary / notes |
| --- | --- | --- | --- | --- |
| HTTP API | FastAPI routes and Pydantic schemas | **REAL APPLICATION LOGIC** | `APP_ENV` | Validates transport; contains no finance rules. |
| Workflow runtime | Explicit bounded LangGraph state graph | **REAL APPLICATION LOGIC** | `AGENT_MAX_STEPS`, `AGENT_MAX_TOOL_CALLS`, `TOOL_MAX_RETRIES` | Fixed routing; model cannot select consequential tools. |
| Live model provider | OpenAI-compatible chat-completions adapter | **LOCAL IMPLEMENTATION** using an external service | `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_TIMEOUT_SECONDS`, `LLM_MAX_RETRIES` | Output is untrusted until schema/citation validation. Disabled mode fails closed. |
| Fake model provider | Deterministic structured-response provider | **TEST DOUBLE** | Injected by tests/evaluation | Exercises the same validation node; not used as a silent live fallback. |
| RAG index | Heading-aware BM25 + sparse TF-IDF + metadata JSON index | **LOCAL IMPLEMENTATION** | `CORPUS_PATH`, `INDEX_PATH`, `RAG_*` | Read-only evidence; relevance is separate from authority/trust. |
| Policy corpus | Supplied Markdown/YAML documents | **SUPPLIED INPUT** | `CORPUS_PATH` | Authoritative test input but untrusted runtime data; source files are never modified. |
| Persistence | SQLAlchemy with SQLite | **LOCAL IMPLEMENTATION** | `DATABASE_URL` | Sole workflow checkpoint, approvals, uniqueness, decisions, and audit history. |
| Vendor tool | `FixtureFinanceTools.get_vendor_record` | **SIMULATED EXTERNAL SYSTEM** | `fixtures/finance/vendors.json` | Typed, bounded, read-only; masked payment metadata only. |
| PO/receipt tool | `FixtureFinanceTools.get_purchase_order` | **SIMULATED EXTERNAL SYSTEM** | `fixtures/finance/purchase_orders.json` | Separates not-found from timeout/transient failure. |
| Invoice-history tool | `FixtureFinanceTools.check_invoice_history` | **SIMULATED EXTERNAL SYSTEM** | `fixtures/finance/invoice_history.json` | Bounded results support deterministic duplicate detection. |
| Invoice case source | Fixture case loader | **SIMULATED EXTERNAL SYSTEM** | `fixtures/finance/cases.json` | Resolves full evidence and rejects public-summary contradictions. |
| Finance controls | Duplicate, match, vendor, risk, currency, authority services | **REAL APPLICATION LOGIC** | Reviewed constants in `app/services/policy_rules.py` | Decimal-only; current-policy traced; RAG cannot configure rules. |
| Approver directory | Fixture approver service | **SIMULATED EXTERNAL SYSTEM** | `fixtures/finance/approvers.json` | Demonstrates role/limit checks; is not enterprise identity proof. |
| Approval service | Workflow/persistence approval resolution | **REAL APPLICATION LOGIC** | Persisted callback key | Human gate, replay semantics, and conflicts are transactionally enforced. |
| Finance submitter | Approval-gated local decision adapter | **SIMULATED EXTERNAL SYSTEM** | Deterministic idempotency key | Cannot move money; independently verifies persisted approval. |
| Audit | Ordered sanitized SQLite audit events | **REAL APPLICATION LOGIC** | Database configuration | Records transitions/outcomes without secrets, full prompts, or full bank details. |
| Evaluation harness | FIN-001–FIN-005 runner over real services | **REAL APPLICATION LOGIC** for acceptance validation | Evaluation fixtures and local RAG index | Fresh database per case; fake model only; no network or paid API. |

The production substitutions and unimplemented operational capabilities are listed once in the
[design note](design-note.md#limitations-and-production-evolution).
