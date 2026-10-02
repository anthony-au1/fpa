import asyncio
from pathlib import Path

from app.rag.contracts import RetrievalQuery
from app.rag.ingestion import build_index
from app.rag.retrieval import LocalFinanceDocumentRetriever
from app.tools.retrieve_finance_documents import retrieve_finance_documents


def test_retrieve_finance_documents_is_typed_read_only_data(tmp_path: Path) -> None:
    build_index(
        Path("finance_rag_corpus"),
        tmp_path,
        embedding_provider="local_tfidf",
        maximum_chunk_chars=1800,
    )
    response = asyncio.run(
        retrieve_finance_documents(
            RetrievalQuery(query="bank account change", top_k=3),
            LocalFinanceDocumentRetriever(tmp_path),
        )
    )
    assert response.results
    assert all(result.citation.chunk_id for result in response.results)
    assert all(not hasattr(result, "tool_calls") for result in response.results)
