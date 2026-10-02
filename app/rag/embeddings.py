import math
from collections import Counter
from typing import Protocol

from app.rag.contracts import EmbeddingState, SparseValue
from app.rag.text import word_ngrams


class EmbeddingProvider(Protocol):
    name: str

    def fit_transform(self, texts: list[str]) -> tuple[EmbeddingState, list[list[SparseValue]]]: ...

    def transform(self, text: str, state: EmbeddingState) -> list[SparseValue]: ...


class LocalTfidfEmbeddingProvider:
    """Deterministic sparse TF-IDF vectors; no model download or credentials required."""

    name = "local_tfidf"

    def fit_transform(self, texts: list[str]) -> tuple[EmbeddingState, list[list[SparseValue]]]:
        document_terms = [set(word_ngrams(text)) for text in texts]
        vocabulary = sorted(set().union(*document_terms)) if document_terms else []
        document_count = len(texts)
        document_frequency = {
            term: sum(term in terms for terms in document_terms) for term in vocabulary
        }
        inverse_document_frequency = [
            round(math.log((1 + document_count) / (1 + document_frequency[term])) + 1, 12)
            for term in vocabulary
        ]
        state = EmbeddingState(
            provider=self.name,
            vocabulary=vocabulary,
            inverse_document_frequency=inverse_document_frequency,
        )
        return state, [self.transform(text, state) for text in texts]

    def transform(self, text: str, state: EmbeddingState) -> list[SparseValue]:
        term_counts = Counter(word_ngrams(text))
        if not term_counts:
            return []
        vocabulary_index = {term: index for index, term in enumerate(state.vocabulary)}
        weighted: list[tuple[int, float]] = []
        for term, count in term_counts.items():
            index = vocabulary_index.get(term)
            if index is not None:
                weight = (1 + math.log(count)) * state.inverse_document_frequency[index]
                weighted.append((index, weight))
        norm = math.sqrt(sum(value * value for _, value in weighted))
        if norm == 0:
            return []
        return [
            SparseValue(index=index, value=round(value / norm, 12))
            for index, value in sorted(weighted)
        ]


def cosine_similarity(left: list[SparseValue], right: list[SparseValue]) -> float:
    left_values = {item.index: item.value for item in left}
    return sum(left_values.get(item.index, 0.0) * item.value for item in right)


def create_embedding_provider(name: str) -> EmbeddingProvider:
    if name == LocalTfidfEmbeddingProvider.name:
        return LocalTfidfEmbeddingProvider()
    raise ValueError(f"Unsupported RAG embedding provider: {name}")
