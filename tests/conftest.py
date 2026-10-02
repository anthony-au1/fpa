from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}")
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def case_payload() -> dict:
    return {
        "case_id": "CASE-001",
        "invoice_reference": "INV-100",
        "vendor": "Example Supplies Pty Ltd",
        "amount": "100.10",
        "currency": "AUD",
    }
