# ADR 0004: Separate consequential action boundary

**Decision:** Keep finance submission outside evidence tools and require persisted human approval plus a unique idempotency key.

**Reason:** Model output and retrieved text must be structurally incapable of directly causing a financial action.
