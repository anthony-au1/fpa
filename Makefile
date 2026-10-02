.PHONY: build up down test lint format format-check ingest retrieve rag-eval finance-demo eval

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

ingest:
	uv run python -m app.rag.cli ingest

retrieve:
	@test -n "$(QUERY)" || (echo 'Usage: make retrieve QUERY="bank account change"' >&2; exit 2)
	uv run python -m app.rag.cli retrieve "$(QUERY)"

rag-eval:
	uv run python -m app.rag.cli evaluate

finance-demo:
	uv run python -m app.services.finance_demo --case "$(or $(CASE),FIN-001)"

eval:
	@echo "FIN evaluation execution is intentionally deferred to a later task." >&2
	@exit 2
