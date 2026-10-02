from pathlib import Path

from app.domain.finance import PolicyReference
from app.domain.models import DocumentAuthority
from app.rag.ingestion import load_corpus
from app.services import policy_rules


def test_all_deterministic_policy_references_exist_in_current_corpus() -> None:
    documents = load_corpus(Path("finance_rag_corpus"))
    current = {
        (document.metadata.document_id, document.metadata.version): document
        for document in documents
        if document.metadata.status is DocumentAuthority.CURRENT
    }
    references = {
        name: value
        for name, value in vars(policy_rules).items()
        if isinstance(value, PolicyReference)
    }
    assert references
    for name, reference in references.items():
        pair = (reference.document_id, reference.version)
        assert pair in current, f"{name} cites missing or non-current policy {pair}"
        headings = {
            line.lstrip("# ").strip()
            for line in current[pair].body.splitlines()
            if line.startswith("#")
        }
        assert reference.section in headings, f"{name} cites absent heading {reference.section}"


def test_every_numeric_rule_has_current_policy_traceability() -> None:
    expected = {
        "GOODS_ABSOLUTE_VARIANCE",
        "GOODS_PERCENT_VARIANCE",
        "SERVICE_ABSOLUTE_VARIANCE",
        "SERVICE_PERCENT_VARIANCE",
        "PROBABLE_DUPLICATE_DAYS",
        "PROBABLE_DUPLICATE_AMOUNT_PERCENT",
        "NEW_VENDOR_DAYS",
        "FRAUD_ESCALATION_INDICATOR_COUNT",
        "AUTHORITY_BANDS",
    }
    assert set(policy_rules.RULE_TRACEABILITY) == expected
    assert all(
        reference.document_id != "FIN-POL-003-OLD"
        for reference in policy_rules.RULE_TRACEABILITY.values()
    )
