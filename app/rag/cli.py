import argparse
import sys
from decimal import Decimal
from pathlib import Path

from app.config import get_settings
from app.rag.contracts import RetrievalQuery
from app.rag.evaluation import evaluate_retrieval, load_evaluation_cases
from app.rag.ingestion import build_index
from app.rag.retrieval import LocalFinanceDocumentRetriever


def _retriever() -> LocalFinanceDocumentRetriever:
    settings = get_settings()
    return LocalFinanceDocumentRetriever(
        settings.index_path,
        timeout_seconds=settings.rag_retrieval_timeout_seconds,
        bm25_weight=settings.rag_bm25_weight,
        vector_weight=settings.rag_vector_weight,
        metadata_weight=settings.rag_metadata_weight,
    )


def ingest() -> int:
    settings = get_settings()
    summary = build_index(
        settings.corpus_path,
        settings.index_path,
        embedding_provider=settings.rag_embedding_provider,
        maximum_chunk_chars=settings.rag_chunk_max_chars,
    )
    print(f"documents indexed: {summary.documents}")
    print(f"chunks created: {summary.chunks}")
    print(f"current documents: {summary.current_documents}")
    print(f"superseded documents: {summary.superseded_documents}")
    print(f"untrusted documents: {summary.untrusted_documents}")
    print(f"irrelevant references: {summary.irrelevant_references}")
    print(f"corpus fingerprint: {summary.corpus_fingerprint}")
    print(f"index: {summary.index_file}")
    return 0


def retrieve(query: str, top_k: int, exclude_superseded: bool) -> int:
    response = _retriever().retrieve_sync(
        RetrievalQuery(
            query=query,
            top_k=top_k,
            include_superseded=not exclude_superseded,
        )
    )
    for rank, result in enumerate(response.results, start=1):
        preview = " ".join(result.content.split())[:160]
        print(
            f"{rank}. {result.document_id} v{result.version} [{result.authority}; "
            f"{result.authority_eligibility}] score={result.relevance}"
        )
        print(f"   {result.heading} | {result.citation.source_filename}")
        print(f"   {preview}")
    return 0


def evaluate(dataset: Path) -> int:
    cases = load_evaluation_cases(dataset)
    metrics = evaluate_retrieval(_retriever(), cases)
    print(f"evaluation cases: {metrics.cases}")
    print(f"HitRate@5: {metrics.hit_rate_at_k:.3f}")
    print(f"Macro Recall@5: {metrics.macro_recall_at_k:.3f}")
    if metrics.hit_rate_at_k < Decimal("1.0") or metrics.macro_recall_at_k < Decimal("0.85"):
        print("RAG evaluation failed acceptance thresholds", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Local finance policy RAG utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("ingest")
    retrieve_parser = subparsers.add_parser("retrieve")
    retrieve_parser.add_argument("query")
    retrieve_parser.add_argument("--top-k", type=int, default=5)
    retrieve_parser.add_argument("--exclude-superseded", action="store_true")
    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument(
        "--dataset", type=Path, default=Path("fixtures/rag_evaluation.json")
    )
    arguments = parser.parse_args()
    if arguments.command == "ingest":
        return ingest()
    if arguments.command == "retrieve":
        return retrieve(arguments.query, arguments.top_k, arguments.exclude_superseded)
    return evaluate(arguments.dataset)


if __name__ == "__main__":
    raise SystemExit(main())
