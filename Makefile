.PHONY: build up down test lint format format-check ingest eval

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
	@echo "RAG ingestion is intentionally deferred to a later task." >&2
	@exit 2

eval:
	@echo "FIN evaluation execution is intentionally deferred to a later task." >&2
	@exit 2
