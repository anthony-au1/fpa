import json
from decimal import Decimal
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.rag.contracts import EvaluationCase, EvaluationMetrics, RetrievalQuery
from app.rag.errors import CorpusValidationError
from app.rag.retrieval import LocalFinanceDocumentRetriever


def load_evaluation_cases(path: Path) -> list[EvaluationCase]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return TypeAdapter(list[EvaluationCase]).validate_python(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise CorpusValidationError(f"Invalid RAG evaluation dataset {path}: {exc}") from exc


def evaluate_retrieval(
    retriever: LocalFinanceDocumentRetriever, cases: list[EvaluationCase]
) -> EvaluationMetrics:
    hits = 0
    recalls: list[Decimal] = []
    for case in cases:
        response = retriever.retrieve_sync(
            RetrievalQuery(
                query=case.query,
                top_k=case.top_k,
                include_superseded=case.include_superseded,
            )
        )
        returned = {result.document_id for result in response.results}
        expected = set(case.expected_document_ids)
        matched = returned & expected
        hits += bool(matched)
        recalls.append(Decimal(len(matched)) / Decimal(len(expected)))
    count = len(cases)
    return EvaluationMetrics(
        cases=count,
        hit_rate_at_k=Decimal(hits) / Decimal(count) if count else Decimal(0),
        macro_recall_at_k=sum(recalls, start=Decimal(0)) / Decimal(count) if count else Decimal(0),
    )
