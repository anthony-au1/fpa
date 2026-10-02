import asyncio
import json
import math
from collections import Counter
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from app.domain.models import Citation, DocumentAuthority, RetrievedDocument
from app.rag.contracts import IndexedChunk, RagIndex, RetrievalQuery, RetrievalResponse
from app.rag.embeddings import cosine_similarity, create_embedding_provider
from app.rag.errors import (
    IndexCompatibilityError,
    IndexNotBuiltError,
    RetrievalTimeoutError,
)
from app.rag.ingestion import INDEX_FILENAME, INDEX_SCHEMA_VERSION
from app.rag.text import tokenize


def _decimal_score(value: float) -> Decimal:
    return Decimal(f"{max(value, 0.0):.6f}")


class LocalFinanceDocumentRetriever:
    def __init__(
        self,
        index_path: Path,
        *,
        timeout_seconds: float = 2,
        bm25_weight: float = 0.5,
        vector_weight: float = 0.35,
        metadata_weight: float = 0.15,
    ) -> None:
        if not math.isclose(bm25_weight + vector_weight + metadata_weight, 1.0):
            raise ValueError("RAG ranking weights must sum to 1.0")
        self.index_file = index_path / INDEX_FILENAME
        self.timeout_seconds = timeout_seconds
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.metadata_weight = metadata_weight
        self.index = self._load_index()
        self.embedding_provider = create_embedding_provider(self.index.embedding.provider)

    def _load_index(self) -> RagIndex:
        if not self.index_file.exists():
            raise IndexNotBuiltError(
                f"RAG index not found at {self.index_file}; run `make ingest` first"
            )
        try:
            raw = json.loads(self.index_file.read_text(encoding="utf-8"))
            index = RagIndex.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise IndexCompatibilityError(f"Invalid RAG index at {self.index_file}: {exc}") from exc
        if index.schema_version != INDEX_SCHEMA_VERSION:
            raise IndexCompatibilityError(
                f"Unsupported RAG index schema {index.schema_version}; "
                f"expected {INDEX_SCHEMA_VERSION}"
            )
        return index

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResponse:
        try:
            async with asyncio.timeout(self.timeout_seconds):
                return await asyncio.to_thread(self.retrieve_sync, query)
        except TimeoutError as exc:
            raise RetrievalTimeoutError(
                f"Retrieval exceeded {self.timeout_seconds:g} seconds"
            ) from exc

    def retrieve_sync(self, query: RetrievalQuery) -> RetrievalResponse:
        candidates = [
            chunk
            for chunk in self.index.chunks
            if query.include_superseded
            or chunk.source.metadata.status != DocumentAuthority.SUPERSEDED
        ]
        query_tokens = tokenize(query.query)
        query_vector = self.embedding_provider.transform(query.query, self.index.embedding)
        bm25_scores = self._bm25_scores(query_tokens, candidates)
        max_bm25 = max(bm25_scores, default=0.0)
        ranked: list[tuple[bool, float, str, str, str, RetrievedDocument]] = []
        normalized_identifier = query.query.strip().casefold()

        for chunk, raw_bm25 in zip(candidates, bm25_scores, strict=True):
            metadata = chunk.source.metadata
            exact_identifier = normalized_identifier == metadata.document_id.casefold()
            bm25 = raw_bm25 / max_bm25 if max_bm25 else 0.0
            vector = cosine_similarity(query_vector, chunk.vector)
            metadata_text = " ".join(
                [metadata.document_id, metadata.title, chunk.source.heading, *metadata.tags]
            )
            metadata_tokens = set(tokenize(metadata_text))
            metadata_score = (
                sum(token in metadata_tokens for token in query_tokens) / len(query_tokens)
                if query_tokens
                else 0.0
            )
            relevance = (
                self.bm25_weight * bm25
                + self.vector_weight * vector
                + self.metadata_weight * metadata_score
            )
            citation = Citation(
                document_id=metadata.document_id,
                version=metadata.version,
                section=chunk.source.heading,
                chunk_id=chunk.source.chunk_id,
                source_filename=metadata.source_filename,
            )
            result = RetrievedDocument(
                document_id=metadata.document_id,
                title=metadata.title,
                version=metadata.version,
                authority=metadata.status,
                authority_eligibility=chunk.source.authority_eligibility,
                authority_reason=chunk.source.authority_reason,
                category=chunk.source.category,
                classification=metadata.classification,
                jurisdiction=metadata.jurisdiction,
                tags=metadata.tags,
                effective_date=metadata.effective_date,
                superseded_date=metadata.superseded_date,
                source_filename=metadata.source_filename,
                chunk_id=chunk.source.chunk_id,
                heading=chunk.source.heading,
                content=chunk.source.text,
                relevance=_decimal_score(relevance),
                score_components={
                    "bm25": _decimal_score(bm25),
                    "vector": _decimal_score(vector),
                    "metadata": _decimal_score(metadata_score),
                },
                citation=citation,
            )
            ranked.append(
                (
                    exact_identifier,
                    relevance,
                    metadata.document_id,
                    chunk.source.heading,
                    chunk.source.chunk_id,
                    result,
                )
            )

        ranked.sort(key=lambda item: (-int(item[0]), -item[1], item[2], item[3], item[4]))
        return RetrievalResponse(
            query=query.query,
            index_fingerprint=self.index.corpus_fingerprint,
            results=[item[-1] for item in ranked[: query.top_k]],
        )

    @staticmethod
    def _bm25_scores(query_tokens: list[str], chunks: list[IndexedChunk]) -> list[float]:
        if not chunks or not query_tokens:
            return [0.0] * len(chunks)
        document_frequency = Counter(
            token for chunk in chunks for token in set(chunk.search_tokens)
        )
        average_length = sum(len(chunk.search_tokens) for chunk in chunks) / len(chunks)
        document_count = len(chunks)
        k1 = 1.5
        b = 0.75
        scores: list[float] = []
        for chunk in chunks:
            frequencies = Counter(chunk.search_tokens)
            length = len(chunk.search_tokens)
            score = 0.0
            for token in query_tokens:
                frequency = frequencies[token]
                if not frequency:
                    continue
                inverse_document_frequency = math.log(
                    1
                    + (document_count - document_frequency[token] + 0.5)
                    / (document_frequency[token] + 0.5)
                )
                denominator = frequency + k1 * (1 - b + b * length / average_length)
                score += inverse_document_frequency * frequency * (k1 + 1) / denominator
            scores.append(score)
        return scores
