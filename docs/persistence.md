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

`runs.state_payload` is a checkpoint envelope for the typed graph state; status and counters are also columns for safe querying. A restart loads the same run and continues only from its persisted boundary. A monotonic version supports optimistic update checks when execution is added.

Approval creation and callbacks use distinct stable idempotency keys. A replay with identical content returns the recorded result; a conflicting reuse is rejected. Only one pending approval may exist for a run. `finance_decisions.run_id` and its idempotency key are unique, guaranteeing one effective consequential decision even when callbacks or downstream requests repeat.

Audit events are append-only and uniquely ordered per run. Events cover transitions, retrievals, calculations, rule applications, tool outcomes/durations, approvals, overrides, and external references. The current foundation records run creation; later workflow work adds the remaining event types.

SQLite foreign keys are enabled on every connection. Writes that change run state, approvals, decisions, and their audit events must share a transaction. Bank accounts, credentials, signatures, tax identifiers, and unnecessary personal details are excluded or masked before storage. The database and future index live in the mounted `data/` directory and must receive production-appropriate encryption/access controls outside this local exercise.
