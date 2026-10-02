# Design note

## Problem framing

Accounts Payable processing is not merely a chatbot or retrieval problem. It combines untrusted
documents, exact monetary controls, incomplete external evidence, policy interpretation, human
authority, and a consequential boundary. A plausible answer is insufficient: the system must explain
which evidence it used, distinguish uncertainty from mismatch, stop before action, and remain safe on
retry or restart.

## Architecture and responsibility split

The application follows a fixed pipeline:

```text
request -> policy retrieval -> finance evidence -> deterministic controls
        -> structured LLM analysis -> constrained recommendation
        -> persisted human approval -> idempotent simulated submission
```

FastAPI is the typed transport boundary. LangGraph makes the workflow and branches explicit, with
persisted step/tool budgets instead of an open-ended ReAct loop. SQLite stores the sole workflow
checkpoint, audit events, approval requests, callback identity, and finance decisions. Fixture-backed
tools simulate external systems without implying real ERP, identity, or payment connectivity.

## Why finance controls are deterministic

Python application code owns Decimal arithmetic, invoice-reference normalization, duplicate identity,
three-way matching, tolerance formulas, evidence requirements, vendor status, authority bands,
outcome precedence, state transitions, approval gating, and idempotency. These are enforceable rules
whose inputs and results must be reproducible and testable. The supplied Markdown is evidence and
traceability, not executable configuration, so a stale or poisoned document cannot change thresholds.

The model is still useful for a narrow task: synthesizing bounded retrieved evidence and deterministic
results into structured, source-linked policy findings, inferences, unknowns, and an explanation. Its
Pydantic schema contains no recommendation outcome or action field. Unknown citation IDs or
non-current authority citations fail validation; deterministic controls always determine the outcome.

## RAG strategy

Ingestion validates YAML metadata and chunks Markdown by heading and section. Stable chunk IDs derive
from source identity and normalized content. The local index combines BM25, sparse TF-IDF cosine
similarity, and metadata token coverage. For a small policy corpus this is deterministic, inspectable,
credential-free, fast, and easier to defend than operating a vector database or downloading a large
embedding model.

Retrieval relevance is deliberately separate from authority and trust. Current policy,
historical-only superseded policy, irrelevant references, and untrusted supplier material can all be
retrieved. Downstream validation admits only current-authority chunks to authoritative findings. The
adversarial supplier document remains verbatim evidence; it cannot mutate prompts, graph state,
finance rules, or tool permissions.

## Workflow, approval, and replay safety

The graph has a fixed node set and no model-directed tool loop. A payment/posting candidate creates one
approval request, persists `WAITING_FOR_APPROVAL`, and returns the HTTP response. A later callback
loads the same run. Rejection completes without submission; approval may continue only after fixture
authority validation.

The simulated submitter independently reads the persisted approval and uses a deterministic financial
decision key. Callback replay identity is the persisted callback key: the same key and same semantic
payload returns the existing result, while changed content or a new key after resolution conflicts.
Database uniqueness provides exactly-once-effective behavior inside this local simulation—not a claim
of distributed exactly-once delivery.

## Failure handling and persistence

`NOT_FOUND` is business evidence; timeout and transient failure are infrastructure uncertainty.
Retryable tool failures receive at most one retry without sleeps in deterministic tests. Missing or
unavailable required evidence cannot become a pass. Model timeouts, retryable provider errors,
malformed JSON, schema errors, and invalid citations use a bounded retry/repair policy before the run
is persisted as `FAILED`.

SQLite is appropriate for a single-node local assessment: it demonstrates durable pauses,
transactional state changes, uniqueness, restart/resume, and append-only audit history without
external infrastructure. Approval is committed before resume, so a crash can be retried. A persisted
decision can be returned after a lost response. Production external submission would add an outbox
and downstream idempotency while preserving the same domain keys.

## Security and data minimization

Safety is structural rather than dependent on a prompt that says “ignore malicious instructions.”
The LLM has no consequential tool permission; graph transitions are application-controlled; the
submitter verifies persistence; current authority is checked in code. Audit payloads contain outcomes,
identifiers, durations, and sanitized summaries rather than API keys, full bank details, full prompts,
or unnecessary private data. This is a take-home demonstration of data minimization and control
boundaries, not a claim of regulatory certification.

## Eight-hour prioritization

The timebox was used for the highest-risk vertical slice: a safe workflow, deterministic controls,
grounded local RAG, bounded model validation, durable human approval, idempotency, explicit failure
handling, and deterministic FIN-001–FIN-005 evaluation. The deliberate choice was a smaller system
whose behavior can be defended rather than speculative infrastructure or autonomous behavior.

## Limitations and production evolution

This section is the authoritative limitations list.

- Vendor, PO/receipt, history, invoice-source, approver, and finance submission adapters are synthetic
  fixtures. Production needs authenticated ERP/vendor/payment adapters and an enterprise identity and
  delegated-authority directory.
- The submitter creates only a local simulated decision. A real external action needs a transactional
  outbox, durable delivery worker, downstream idempotency, reconciliation, and operational recovery.
- SQLite is single-node local persistence with no distributed locking. Production should use a
  managed transactional database, migrations, encryption, backup, and concurrency controls.
- Retrieval is deterministic lexical BM25/TF-IDF over a memory-resident JSON index. A larger or
  multilingual corpus may justify approved semantic embeddings, ACL-aware retrieval, incremental
  indexing, and a scalable store.
- There is no corporate FX source, live tax/sanctions service, or real bank-change verification.
  Missing evidence remains unknown rather than being fabricated.
- The OpenAI-compatible live-model adapter requires external provider/model/key configuration. Stable
  tests and evaluations intentionally use a fake provider and therefore do not measure live-model
  quality, drift, latency, or cost.
- Observability is a sanitized append-only audit trail, not a production telemetry, alerting, or model
  monitoring platform. No cloud infrastructure, UI, second model, or automatic escalation exists.
