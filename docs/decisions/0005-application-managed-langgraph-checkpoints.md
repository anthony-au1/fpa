# ADR 0005: Application-managed LangGraph checkpoints

## Decision

Use `runs.state_payload` as the sole durable workflow checkpoint. LangGraph supplies explicit routing
but no separate checkpointer. Each node stores a typed snapshot, counters, next stage, audit event, and
run status in SQLite.

## Rationale

The repository already owns run, approval, audit, and idempotency transactions. A second LangGraph
checkpoint store would duplicate authority and complicate approval crash recovery for this small local
system. Reinvocation dispatches from the persisted next stage using the same run ID.

## Consequences

Node code deliberately coordinates persistence. SQLite transactions make approval and simulated
submission reproducible locally. Production could adopt a database-backed LangGraph checkpointer only
if ownership and transaction boundaries are unified rather than mirrored.
