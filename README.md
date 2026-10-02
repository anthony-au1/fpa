# Financial Processing Agent

Foundation for a controlled Accounts Payable agent. It includes deterministic local finance-policy ingestion and retrieval, domain contracts, a persisted run API, an explicit LangGraph topology, audit/idempotency constraints, and safety boundaries. Reconciliation, workflow execution, approvals, finance submission, and FIN scenario evaluation remain deferred.

## Quick start

```bash
cp .env.example .env
make build
make ingest
make rag-eval
make up
make test
make down
```

Inspect retrieval with `make retrieve QUERY="bank account change"`. The RAG implementation is fully local and simulated: it uses deterministic TF-IDF vectors plus lexical ranking and requires no model credentials or external service. `make eval` still exits with an explanatory error because FIN workflow evaluation is not implemented. API documentation is available at `http://localhost:8000/docs` while the service is running.
