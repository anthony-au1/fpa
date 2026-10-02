from pathlib import Path

import pytest

from app.agent.graph import InvalidModelCitation, _validate_analysis_citations
from app.domain.workflow import PolicyAnalysis
from app.rag.contracts import RetrievalQuery
from app.rag.ingestion import build_index
from app.rag.retrieval import LocalFinanceDocumentRetriever


def test_superseded_chunk_cannot_support_authoritative_policy_finding(tmp_path: Path) -> None:
    build_index(
        Path("finance_rag_corpus"),
        tmp_path,
        embedding_provider="local_tfidf",
        maximum_chunk_chars=1800,
    )
    documents = (
        LocalFinanceDocumentRetriever(tmp_path)
        .retrieve_sync(
            RetrievalQuery(query="delegated financial authority approval thresholds", top_k=20)
        )
        .results
    )
    historical = next(item for item in documents if item.document_id == "FIN-POL-003-OLD")
    analysis = PolicyAnalysis(
        sourced_findings=[],
        policy_findings=[
            {
                "finding_id": "historical-as-current",
                "rule": "old authority",
                "explanation": "must not be authoritative",
                "citation_chunk_ids": [historical.chunk_id],
            }
        ],
        inferences=[],
        unknowns=[],
        explanation="invalid authority use",
        confidence="0.1",
    )
    with pytest.raises(InvalidModelCitation, match="current-authority"):
        _validate_analysis_citations(analysis, documents)


def test_superseded_chunk_may_remain_historical_evidence(tmp_path: Path) -> None:
    build_index(
        Path("finance_rag_corpus"),
        tmp_path,
        embedding_provider="local_tfidf",
        maximum_chunk_chars=1800,
    )
    documents = (
        LocalFinanceDocumentRetriever(tmp_path)
        .retrieve_sync(
            RetrievalQuery(query="delegated financial authority approval thresholds", top_k=20)
        )
        .results
    )
    historical = next(item for item in documents if item.document_id == "FIN-POL-003-OLD")
    analysis = PolicyAnalysis(
        sourced_findings=[
            {
                "finding_id": "historical-evidence",
                "statement": "A superseded version exists",
                "citation_chunk_ids": [historical.chunk_id],
            }
        ],
        policy_findings=[],
        inferences=[],
        unknowns=[],
        explanation="historical context only",
        confidence="0.9",
    )
    _validate_analysis_citations(analysis, documents)
