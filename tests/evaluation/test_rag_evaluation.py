from decimal import Decimal
from pathlib import Path

from app.rag.evaluation import evaluate_retrieval, load_evaluation_cases
from app.rag.ingestion import build_index
from app.rag.retrieval import LocalFinanceDocumentRetriever


def test_rag_evaluation_meets_acceptance_thresholds(tmp_path: Path) -> None:
    build_index(
        Path("finance_rag_corpus"),
        tmp_path,
        embedding_provider="local_tfidf",
        maximum_chunk_chars=1800,
    )
    cases = load_evaluation_cases(Path("fixtures/rag_evaluation.json"))
    metrics = evaluate_retrieval(LocalFinanceDocumentRetriever(tmp_path), cases)
    assert metrics.hit_rate_at_k == Decimal("1")
    assert metrics.macro_recall_at_k >= Decimal("0.85")
