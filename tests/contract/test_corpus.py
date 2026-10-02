from pathlib import Path


def test_corpus_contains_control_documents() -> None:
    corpus = Path("finance_rag_corpus")
    current = (corpus / "03_delegated_financial_authority.md").read_text()
    superseded = (corpus / "delegated_financial_authority_v1.md").read_text()
    adversarial = (corpus / "supplier_payment_instructions.md").read_text()
    irrelevant = (corpus / "travel_policy_extract.md").read_text()
    assert "status: current" in current
    assert "status: superseded" in superseded
    assert "status: untrusted" in adversarial
    assert "unrelated" in irrelevant
