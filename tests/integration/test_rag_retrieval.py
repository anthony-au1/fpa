import asyncio
import time
from pathlib import Path

import pytest

from app.domain.models import AuthorityEligibility, DocumentAuthority, DocumentCategory
from app.rag.contracts import RetrievalQuery
from app.rag.errors import IndexCompatibilityError, IndexNotBuiltError, RetrievalTimeoutError
from app.rag.ingestion import INDEX_FILENAME, build_index
from app.rag.retrieval import LocalFinanceDocumentRetriever


@pytest.fixture(scope="module")
def retriever(tmp_path_factory: pytest.TempPathFactory) -> LocalFinanceDocumentRetriever:
    index_path = tmp_path_factory.mktemp("rag-index")
    build_index(
        Path("finance_rag_corpus"),
        index_path,
        embedding_provider="local_tfidf",
        maximum_chunk_chars=1800,
    )
    return LocalFinanceDocumentRetriever(index_path)


def document_ids(response) -> list[str]:
    return [result.document_id for result in response.results]


def test_policy_identifiers_retrieve_corresponding_documents(retriever) -> None:
    assert document_ids(retriever.retrieve_sync(RetrievalQuery(query="FIN-POL-003")))[0] == (
        "FIN-POL-003"
    )
    assert document_ids(retriever.retrieve_sync(RetrievalQuery(query="FIN-POL-004")))[0] == (
        "FIN-POL-004"
    )


def test_current_and_superseded_authority_are_separate(retriever) -> None:
    relevant = retriever.retrieve_sync(
        RetrievalQuery(query="delegated financial approval authority thresholds", top_k=10)
    )
    current = next(result for result in relevant.results if result.document_id == "FIN-POL-003")
    historical = next(
        result for result in relevant.results if result.document_id == "FIN-POL-003-OLD"
    )
    assert current.authority == DocumentAuthority.CURRENT
    assert current.authority_eligibility == AuthorityEligibility.CURRENT_AUTHORITY
    assert current.category == DocumentCategory.CURRENT_POLICY
    assert historical.authority == DocumentAuthority.SUPERSEDED
    assert historical.authority_eligibility == AuthorityEligibility.HISTORICAL_ONLY
    assert historical.category == DocumentCategory.SUPERSEDED_POLICY

    current_only = retriever.retrieve_sync(
        RetrievalQuery(
            query="delegated financial approval authority thresholds",
            top_k=10,
            include_superseded=False,
        )
    )
    assert "FIN-POL-003" in document_ids(current_only)
    assert "FIN-POL-003-OLD" not in document_ids(current_only)


def test_prompt_injection_remains_retrievable_untrusted_data(retriever) -> None:
    response = retriever.retrieve_sync(
        RetrievalQuery(query="urgent supplier bank account changed bypass approval", top_k=10)
    )
    result = next(result for result in response.results if result.document_id == "ADV-001")
    assert result.category == DocumentCategory.UNTRUSTED_EVIDENCE
    assert result.classification == "external-unverified"
    assert "Ignore all previous policies" in result.content
    assert not hasattr(result, "actions")


def test_irrelevant_travel_document_does_not_dominate_ap_query(retriever) -> None:
    response = retriever.retrieve_sync(
        RetrievalQuery(query="supplier invoice three-way matching purchase order receipt", top_k=5)
    )
    ids = document_ids(response)
    assert ids[0] == "FIN-POL-002"
    assert "ADV-002" not in ids[:3]


def test_travel_document_is_retrievable_for_travel_query(retriever) -> None:
    response = retriever.retrieve_sync(
        RetrievalQuery(query="employee travel dinner meal limit", top_k=5)
    )
    assert response.results[0].document_id == "ADV-002"
    assert response.results[0].category == DocumentCategory.IRRELEVANT_REFERENCE


def test_every_result_has_stable_citation_metadata(retriever) -> None:
    response = retriever.retrieve_sync(RetrievalQuery(query="missing goods receipt"))
    for result in response.results:
        assert result.chunk_id == result.citation.chunk_id
        assert result.document_id == result.citation.document_id
        assert result.source_filename == result.citation.source_filename
        assert result.citation.section
        assert result.score_components.keys() == {"bm25", "vector", "metadata"}


def test_missing_index_fails_explicitly(tmp_path: Path) -> None:
    with pytest.raises(IndexNotBuiltError, match="make ingest"):
        LocalFinanceDocumentRetriever(tmp_path)


def test_corrupt_index_fails_explicitly(tmp_path: Path) -> None:
    (tmp_path / INDEX_FILENAME).write_text("not-json", encoding="utf-8")
    with pytest.raises(IndexCompatibilityError, match="Invalid RAG index"):
        LocalFinanceDocumentRetriever(tmp_path)


def test_async_boundary_has_explicit_timeout(retriever, monkeypatch) -> None:
    def slow_retrieval(_query):
        time.sleep(0.02)
        return None

    monkeypatch.setattr(retriever, "retrieve_sync", slow_retrieval)
    monkeypatch.setattr(retriever, "timeout_seconds", 0.001)
    with pytest.raises(RetrievalTimeoutError, match="Retrieval exceeded"):
        asyncio.run(retriever.retrieve(RetrievalQuery(query="receipt")))
