from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import DocumentAuthority, RetrievedDocument


class RagModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CorpusDocument(RagModel):
    document_id: str
    title: str
    version: str | None = None
    status: DocumentAuthority
    metadata: dict[str, str | list[str]] = Field(default_factory=dict)
    body: str


class RetrievalQuery(RagModel):
    text: str
    limit: int = Field(default=5, ge=1, le=20)
    include_historical: bool = False


class Retriever(Protocol):
    async def retrieve(self, query: RetrievalQuery) -> list[RetrievedDocument]: ...
