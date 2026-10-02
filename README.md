# Financial Processing Agent

Foundation for a controlled Accounts Payable agent. It defines domain contracts, a persisted run API, an explicit LangGraph topology, audit/idempotency constraints, and safety boundaries. Full RAG, reconciliation, approval execution, finance submission, and FIN scenario evaluation are intentionally deferred.

## Quick start

```bash
cp .env.example .env
make build
make up
make test
make down
```

`make ingest` and `make eval` currently exit with an explanatory error rather than simulate unimplemented behavior. API documentation is available at `http://localhost:8000/docs` while the service is running.
