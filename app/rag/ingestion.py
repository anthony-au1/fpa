import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.domain.models import AuthorityEligibility, DocumentAuthority, DocumentCategory
from app.rag.contracts import (
    CorpusDocument,
    DocumentMetadata,
    IndexedChunk,
    IngestionSummary,
    RagIndex,
    SourceChunk,
)
from app.rag.embeddings import create_embedding_provider
from app.rag.errors import CorpusValidationError
from app.rag.text import normalized_text, tokenize

INDEX_SCHEMA_VERSION = 1
INDEX_FILENAME = "rag-index-v1.json"
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def parse_document(path: Path) -> CorpusDocument:
    raw = path.read_text(encoding="utf-8")
    match = FRONT_MATTER.match(raw)
    if match is None:
        raise CorpusValidationError(f"{path.name}: missing or malformed YAML front matter")
    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise CorpusValidationError(f"{path.name}: invalid YAML front matter: {exc}") from exc
    if not isinstance(loaded, dict):
        raise CorpusValidationError(f"{path.name}: YAML front matter must be a mapping")
    metadata_input: dict[str, Any] = dict(loaded)
    metadata_input["source_filename"] = path.name
    try:
        metadata = DocumentMetadata.model_validate(metadata_input)
    except ValidationError as exc:
        raise CorpusValidationError(f"{path.name}: metadata validation failed: {exc}") from exc
    body = match.group(2).strip()
    if not body:
        raise CorpusValidationError(f"{path.name}: document body is empty")
    return CorpusDocument(
        metadata=metadata,
        body=body,
        source_checksum=hashlib.sha256(raw.encode()).hexdigest(),
    )


def load_corpus(corpus_path: Path) -> list[CorpusDocument]:
    paths = sorted(corpus_path.glob("*.md"))
    if not paths:
        raise CorpusValidationError(f"No Markdown documents found in {corpus_path}")
    documents = [parse_document(path) for path in paths]
    duplicate_ids = [
        document_id
        for document_id, count in Counter(
            document.metadata.document_id for document in documents
        ).items()
        if count > 1
    ]
    if duplicate_ids:
        raise CorpusValidationError(
            f"Duplicate document_id values: {', '.join(sorted(duplicate_ids))}"
        )
    return documents


def _classification(
    metadata: DocumentMetadata,
) -> tuple[AuthorityEligibility, str, DocumentCategory]:
    if "irrelevant" in metadata.tags:
        return (
            AuthorityEligibility.NON_AUTHORITY,
            "metadata identifies this as an irrelevant reference",
            DocumentCategory.IRRELEVANT_REFERENCE,
        )
    if metadata.status == DocumentAuthority.CURRENT:
        return (
            AuthorityEligibility.CURRENT_AUTHORITY,
            "current policy metadata",
            DocumentCategory.CURRENT_POLICY,
        )
    if metadata.status == DocumentAuthority.SUPERSEDED:
        return (
            AuthorityEligibility.HISTORICAL_ONLY,
            "superseded policy retained for history",
            DocumentCategory.SUPERSEDED_POLICY,
        )
    return (
        AuthorityEligibility.EVIDENCE_ONLY,
        "untrusted source metadata; evidence only",
        DocumentCategory.UNTRUSTED_EVIDENCE,
    )


def _split_oversized(text: str, maximum: int) -> list[str]:
    paragraphs = [
        paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()
    ]
    parts: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidates = [paragraph]
        if len(paragraph) > maximum:
            candidates = []
            remainder = paragraph
            while len(remainder) > maximum:
                split_at = remainder.rfind(" ", 0, maximum + 1)
                split_at = split_at if split_at > 0 else maximum
                candidates.append(remainder[:split_at].strip())
                remainder = remainder[split_at:].strip()
            if remainder:
                candidates.append(remainder)
        for candidate in candidates:
            combined = f"{current}\n\n{candidate}".strip()
            if current and len(combined) > maximum:
                parts.append(current)
                current = candidate
            else:
                current = combined
    if current:
        parts.append(current)
    return parts


def chunk_document(document: CorpusDocument, maximum_chars: int) -> list[SourceChunk]:
    sections: list[tuple[str, list[str]]] = []
    heading_stack: list[str] = []
    current_lines: list[str] = []
    current_heading = document.metadata.title

    def flush() -> None:
        nonlocal current_lines
        text = "\n".join(current_lines).strip()
        if text:
            sections.append((current_heading, current_lines))
        current_lines = []

    for line in document.body.splitlines():
        match = HEADING.match(line)
        if match:
            flush()
            level = len(match.group(1))
            title = match.group(2).strip()
            heading_stack[:] = heading_stack[: level - 1]
            heading_stack.append(title)
            current_heading = " > ".join(heading_stack)
        else:
            current_lines.append(line)
    flush()

    eligibility, reason, category = _classification(document.metadata)
    chunks: list[SourceChunk] = []
    for heading, lines in sections:
        section_text = "\n".join(lines).strip()
        for part, text in enumerate(_split_oversized(section_text, maximum_chars), start=1):
            identity = "\n".join(
                [
                    document.metadata.document_id,
                    document.metadata.version,
                    heading,
                    str(part),
                    normalized_text(text),
                ]
            )
            digest = hashlib.sha256(identity.encode()).hexdigest()[:20]
            chunks.append(
                SourceChunk(
                    chunk_id=f"chunk-{digest}",
                    metadata=document.metadata,
                    heading=heading,
                    part=part,
                    text=text,
                    authority_eligibility=eligibility,
                    authority_reason=reason,
                    category=category,
                )
            )
    if not chunks:
        raise CorpusValidationError(
            f"{document.metadata.source_filename}: no content chunks created"
        )
    return chunks


def _search_text(chunk: SourceChunk) -> str:
    metadata = chunk.metadata
    return "\n".join(
        [
            metadata.document_id,
            metadata.title,
            chunk.heading,
            " ".join(metadata.tags),
            chunk.text,
        ]
    )


def build_index(
    corpus_path: Path,
    index_path: Path,
    *,
    embedding_provider: str,
    maximum_chunk_chars: int,
) -> IngestionSummary:
    documents = load_corpus(corpus_path)
    chunks = [
        chunk for document in documents for chunk in chunk_document(document, maximum_chunk_chars)
    ]
    provider = create_embedding_provider(embedding_provider)
    search_texts = [_search_text(chunk) for chunk in chunks]
    embedding_state, vectors = provider.fit_transform(search_texts)
    indexed_chunks = [
        IndexedChunk(source=chunk, search_tokens=tokenize(_search_text(chunk)), vector=vector)
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    fingerprint_input = "\n".join(
        f"{doc.metadata.source_filename}:{doc.source_checksum}" for doc in documents
    )
    corpus_fingerprint = hashlib.sha256(fingerprint_input.encode()).hexdigest()
    index = RagIndex(
        schema_version=INDEX_SCHEMA_VERSION,
        corpus_fingerprint=corpus_fingerprint,
        embedding=embedding_state,
        chunks=indexed_chunks,
    )
    index_path.mkdir(parents=True, exist_ok=True)
    destination = index_path / INDEX_FILENAME
    temporary = destination.with_suffix(".tmp")
    serialized = json.dumps(index.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    temporary.write_text(serialized + "\n", encoding="utf-8")
    os.replace(temporary, destination)
    status_counts = Counter(document.metadata.status for document in documents)
    return IngestionSummary(
        documents=len(documents),
        chunks=len(chunks),
        current_documents=status_counts[DocumentAuthority.CURRENT],
        superseded_documents=status_counts[DocumentAuthority.SUPERSEDED],
        untrusted_documents=status_counts[DocumentAuthority.UNTRUSTED],
        irrelevant_references=sum("irrelevant" in document.metadata.tags for document in documents),
        corpus_fingerprint=corpus_fingerprint,
        index_file=str(destination),
    )
