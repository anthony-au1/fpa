from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.llm.provider import FakeModelProvider
from app.main import create_app
from app.rag.ingestion import build_index

VALID_ANALYSIS = {
    "sourced_findings": [],
    "policy_findings": [],
    "inferences": [],
    "unknowns": [],
    "explanation": "Grounded policy analysis",
    "confidence": "0.90",
}


@pytest.fixture
def client(tmp_path: Path):
    index_path = tmp_path / "index"
    build_index(
        Path("finance_rag_corpus"),
        index_path,
        embedding_provider="local_tfidf",
        maximum_chunk_chars=1800,
    )
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", index_path=index_path)
    app = create_app(settings, model_provider=FakeModelProvider([VALID_ANALYSIS]))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def case_payload() -> dict:
    return {
        "case_id": "FIN-001",
        "invoice_reference": "INV-001",
        "vendor": "Acme Supplies Pty Ltd",
        "amount": "1100",
        "currency": "AUD",
        "purchase_order_reference": "PO-1001",
    }
