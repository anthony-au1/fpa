# ADR 0002: Local SQLite persistence

**Decision:** Use SQLAlchemy with SQLite, database uniqueness for idempotency, and append-only audit events.

**Reason:** It demonstrates restart/resume and concurrency constraints within the assessment timebox without operating external infrastructure.
