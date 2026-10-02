# Financial Processing Agent

A local, production-minded Accounts Payable workflow using FastAPI, LangGraph, deterministic finance controls, local RAG, SQLite checkpoints, structured model analysis, explicit human approval, and an idempotent simulated finance decision.

## Quick start

```bash
cp .env.example .env
make build
make ingest
make rag-eval
make eval
make up
make test
```

`LLM_PROVIDER=disabled` is fail-closed. For live use, configure an OpenAI-compatible endpoint with the provider's documented model identifier:

```dotenv
LLM_PROVIDER=openai_compatible
LLM_MODEL=<provider-model-id>
LLM_BASE_URL=https://provider.example/v1
LLM_API_KEY=<secret>
```

The application does not silently substitute a fake model. Automated tests inject a deterministic fake and never use live credentials. `LLM_COMPLEX_MODEL` is reserved; there is no automatic model routing.

## API flow

Start a supported synthetic case:

```bash
curl -s http://localhost:8000/runs \
  -H 'content-type: application/json' \
  -d '{"financial_case":{"case_id":"FIN-001","invoice_reference":"INV-001","vendor":"Acme Supplies Pty Ltd","amount":"1100","currency":"AUD","purchase_order_reference":"PO-1001"}}'
```

The response stops at `WAITING_FOR_APPROVAL`; no finance decision exists. Resolve it explicitly:

```bash
curl -s http://localhost:8000/runs/RUN_ID/approval \
  -H 'content-type: application/json' \
  -d '{"approval":{"decision":"APPROVE","approver_id":"manager-1","approver_role":"Cost Centre Manager","idempotency_key":"review-001"}}'
```

An identical replay returns the same decision. A conflicting callback returns HTTP 409. `GET /runs/RUN_ID` returns the persisted workflow snapshot, pending approval when applicable, simulated decision, and sanitized audit events.

`GET /evaluations` lists FIN-001 through FIN-005. `POST /evaluations/run` executes all five through
the real workflow with isolated temporary databases, fixture-backed integrations, the actual local RAG
index, and a deterministic fake model. It never requires live model credentials.

Run a credential-free successful transcript with `make workflow-demo`. Inspect RAG with `make retrieve QUERY="bank account change"`.

## Real and simulated components

- Local Markdown RAG and SQLite persistence are real implementations.
- Finance tools, full invoice evidence, approver directory, and finance submission are explicitly fixture-backed simulations.
- The finance submission only creates an idempotent local record. It cannot post to an ERP, release payment, update banking data, or move money.
- The fixture approver directory is not real identity or corporate-authority validation.
- Live model calls are optional; stable tests use an injected fake provider.

The public request is a summary `FinancialCase`. For this assessment, line-level invoice evidence is loaded by case ID and summary fields must agree. Unknown or contradictory cases fail explicitly.

## Commands

- `make lint`, `make format-check`, `make test`
- `make ingest`, `make rag-eval`, `make retrieve QUERY="..."`
- `make finance-demo`, `make workflow-demo`
- `make eval`, `make eval-samples`
- `make up`, `make down`

`make eval` rebuilds the local index, prints a concise five-case summary, and returns non-zero on any
failed assertion. Use `uv run python -m app.evaluation.cli --json` for machine-readable results.

See `docs/workflow.md`, `docs/finance-controls.md`, `docs/rag.md`, `docs/persistence.md`, and
`docs/evaluation.md` for trust boundaries, retries, checkpoints, approval safety, acceptance coverage,
and production limitations.
