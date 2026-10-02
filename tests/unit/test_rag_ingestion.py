from pathlib import Path

import pytest

from app.domain.models import AuthorityEligibility, DocumentCategory
from app.rag.errors import CorpusValidationError
from app.rag.ingestion import build_index, chunk_document, load_corpus, parse_document


def test_supplied_metadata_is_parsed_and_preserved() -> None:
    document = parse_document(Path("finance_rag_corpus/04_vendor_onboarding_and_bank_changes.md"))
    metadata = document.metadata
    assert metadata.document_id == "FIN-POL-004"
    assert metadata.version == "5.1"
    assert metadata.effective_date.isoformat() == "2026-05-15"
    assert metadata.classification == "restricted"
    assert metadata.source_filename == "04_vendor_onboarding_and_bank_changes.md"
    assert "bank-account" in metadata.tags


def test_all_supplied_documents_are_loaded() -> None:
    documents = load_corpus(Path("finance_rag_corpus"))
    assert len(documents) == 15
    assert len({document.metadata.document_id for document in documents}) == 15


def test_malformed_metadata_fails_with_filename(tmp_path: Path) -> None:
    invalid = tmp_path / "broken.md"
    invalid.write_text("---\ntitle: Missing fields\n---\n# Body\n\nText", encoding="utf-8")
    with pytest.raises(CorpusValidationError, match="broken.md: metadata validation failed"):
        parse_document(invalid)


def test_chunking_preserves_headings_citations_and_stable_ids() -> None:
    document = parse_document(Path("finance_rag_corpus/02_three_way_matching_and_tolerances.md"))
    first = chunk_document(document, 1800)
    second = chunk_document(document, 1800)
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert all(chunk.text.strip() for chunk in first)
    assert any("2. Tolerances" in chunk.heading for chunk in first)
    assert all(chunk.metadata.source_filename for chunk in first)


def test_authority_classification_comes_from_metadata() -> None:
    documents = {
        document.metadata.document_id: document
        for document in load_corpus(Path("finance_rag_corpus"))
    }
    old = chunk_document(documents["FIN-POL-003-OLD"], 1800)[0]
    adversarial = chunk_document(documents["ADV-001"], 1800)[0]
    travel = chunk_document(documents["ADV-002"], 1800)[0]
    assert old.authority_eligibility == AuthorityEligibility.HISTORICAL_ONLY
    assert adversarial.category == DocumentCategory.UNTRUSTED_EVIDENCE
    assert travel.category == DocumentCategory.IRRELEVANT_REFERENCE


def test_rebuild_is_byte_deterministic(tmp_path: Path) -> None:
    summary_one = build_index(
        Path("finance_rag_corpus"),
        tmp_path,
        embedding_provider="local_tfidf",
        maximum_chunk_chars=1800,
    )
    first = (tmp_path / "rag-index-v1.json").read_bytes()
    summary_two = build_index(
        Path("finance_rag_corpus"),
        tmp_path,
        embedding_provider="local_tfidf",
        maximum_chunk_chars=1800,
    )
    second = (tmp_path / "rag-index-v1.json").read_bytes()
    assert first == second
    assert summary_one.corpus_fingerprint == summary_two.corpus_fingerprint
    assert summary_one.documents == 15
    assert summary_one.chunks == summary_two.chunks
