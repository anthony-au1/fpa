# Persistence and idempotency

SQLite is sufficient for the local assessment and demonstrates durable state, restart/resume, uniqueness, and audit history without external infrastructure.

```mermaid
erDiagram
    RUNS ||--o{ AUDIT_EVENTS : records
    RUNS ||--o{ APPROVAL_REQUESTS : requests
    RUNS ||--o| FINANCE_DECISIONS : produces
    RUNS {
      string id PK
      string status
      json case_payload
      json state_payload
      int version
      int step_count
      int tool_call_count
    }
    AUDIT_EVENTS {
      string id PK
      string run_id FK
      int sequence UK
      string event_type
      json payload
    }
    APPROVAL_REQUESTS {
      string id PK
      string run_id FK
      string status
      string idempotency_key UK
      string callback_idempotency_key UK
    }
    FINANCE_DECISIONS {
      string id PK
      string run_id FK_UK
      string idempotency_key UK
      string external_reference
    }
```

`runs.state_payload` is the sole checkpoint envelope for typed workflow state; status and counters are also columns for safe querying. Every node records its next resumable stage. LangGraph has no competing checkpoint store. A restart loads the same run and continues only from that persisted boundary. The monotonic version remains available for stronger optimistic concurrency in production.

Approval creation and callbacks use distinct stable idempotency keys. The same persisted callback key
with the same semantic payload returns the recorded result. The same key with changed content, or a
different key after resolution, is rejected without changing history. Only one pending approval may
exist for a run. `finance_decisions.run_id` and its idempotency key are unique, guaranteeing one
effective local consequential decision even when callbacks or downstream requests repeat.

Audit events are append-only and uniquely ordered per run. Events cover nodes, retrieval, every tool/model attempt, reconciliation, recommendation, approval, resume, submission, replay, completion, and failure. Payloads are sanitized before persistence.

Approval resolution is committed before graph resume. An identical callback can therefore resume after a crash. The simulated finance decision and completion checkpoint share the request transaction; uniqueness on run and idempotency key prevents duplicate effective decisions. A real external finance API would require a transactional outbox plus the same downstream idempotency key.

SQLite foreign keys are enabled on every connection. Writes that change run state, approvals, decisions, and their audit events must share a transaction. Bank accounts, credentials, signatures, tax identifiers, and unnecessary personal details are excluded or masked before storage. The database and future index live in the mounted `data/` directory and must receive production-appropriate encryption/access controls outside this local exercise.
