import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.domain.finance import InvoiceEvidence
from app.domain.models import FinancialCase


class CaseEvidenceError(ValueError):
    pass


class FixtureCaseEvidenceLoader:
    """Simulated invoice-source boundary keyed by the public case ID."""

    def __init__(self, fixture_file: Path) -> None:
        try:
            cases = TypeAdapter(list[InvoiceEvidence]).validate_python(
                json.loads(fixture_file.read_text())
            )
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise CaseEvidenceError(f"Invalid case evidence fixture: {exc}") from exc
        self._cases = {case.case_id: case for case in cases}

    def load(self, financial_case: FinancialCase) -> InvoiceEvidence:
        evidence = self._cases.get(financial_case.case_id)
        if evidence is None:
            raise CaseEvidenceError(
                f"No simulated invoice evidence exists for case {financial_case.case_id}"
            )
        mismatches = []
        checks = {
            "invoice_reference": (
                financial_case.invoice_reference,
                evidence.invoice_reference,
            ),
            "vendor": (financial_case.vendor, evidence.vendor_legal_name),
            "amount": (financial_case.amount, evidence.gross_amount),
            "currency": (financial_case.currency, evidence.currency),
        }
        for field, (request_value, evidence_value) in checks.items():
            if request_value != evidence_value:
                mismatches.append(field)
        if financial_case.purchase_order_reference not in {None, evidence.purchase_order_id}:
            mismatches.append("purchase_order_reference")
        if mismatches:
            raise CaseEvidenceError(
                "FinancialCase conflicts with invoice evidence: " + ", ".join(mismatches)
            )
        return evidence
