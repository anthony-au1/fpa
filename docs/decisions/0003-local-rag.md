# ADR 0003: Local metadata-aware RAG

**Decision:** Use a small local embedding index with heading-aware chunks and mandatory authority metadata.

**Reason:** The corpus is small; an external vector service adds cost and operational complexity without improving the control model.
