from datetime import date
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.models import (
    AuthorityEligibility,
    DocumentAuthority,
    DocumentCategory,
    RetrievedDocument,
)


class RagModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentMetadata(RagModel):
    document_id: str
    title: str
    version: str
    effective_date: date
    superseded_date: date | None = None
    status: DocumentAuthority
    owner: str
    classification: str
    jurisdiction: str
    tags: list[str]
    source_filename: str

    @field_validator("version", mode="before")
    @classmethod
    def normalize_version(cls, value: object) -> str:
        if isinstance(value, str | int | float):
            return str(value)
        raise ValueError("version must be a string or number")


class CorpusDocument(RagModel):
    metadata: DocumentMetadata
    body: str
    source_checksum: str


class SourceChunk(RagModel):
    chunk_id: str
    metadata: DocumentMetadata
    heading: str
    part: int = Field(ge=1)
    text: str = Field(min_length=1)
    authority_eligibility: AuthorityEligibility
    authority_reason: str
    category: DocumentCategory


class SparseValue(RagModel):
    index: int = Field(ge=0)
    value: float


class IndexedChunk(RagModel):
    source: SourceChunk
    search_tokens: list[str]
    vector: list[SparseValue]


class EmbeddingState(RagModel):
    provider: str
    vocabulary: list[str]
    inverse_document_frequency: list[float]


class RagIndex(RagModel):
    schema_version: int
    corpus_fingerprint: str
    embedding: EmbeddingState
    chunks: list[IndexedChunk]


class RetrievalQuery(RagModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    include_superseded: bool = True


class RetrievalResponse(RagModel):
    query: str
    index_fingerprint: str
    results: list[RetrievedDocument]


class Retriever(Protocol):
    async def retrieve(self, query: RetrievalQuery) -> RetrievalResponse: ...


class IngestionSummary(RagModel):
    documents: int
    chunks: int
    current_documents: int
    superseded_documents: int
    untrusted_documents: int
    irrelevant_references: int
    corpus_fingerprint: str
    index_file: str


class EvaluationCase(RagModel):
    evaluation_id: str
    query: str
    expected_document_ids: list[str] = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    include_superseded: bool = True


class EvaluationMetrics(RagModel):
    cases: int
    hit_rate_at_k: Decimal
    macro_recall_at_k: Decimal
