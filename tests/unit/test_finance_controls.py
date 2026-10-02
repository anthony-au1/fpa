from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.finance import ApprovalRole, InvoiceEvidence
from app.domain.models import RecommendationOutcome
from app.services.finance_controls import choose_outcome, required_authority
from app.services.normalization import (
    normalize_invoice_reference,
    punctuation_insensitive_reference,
)


def test_invoice_reference_normalization_is_controlled() -> None:
    assert normalize_invoice_reference(" inv-  001 ") == "INV- 001"
    assert punctuation_insensitive_reference("inv-001/A") == "INV001A"


def test_money_rejects_float() -> None:
    with pytest.raises(ValidationError, match="Decimal-compatible"):
        InvoiceEvidence.model_validate(
            {
                "case_id": "X",
                "vendor_id": "V",
                "vendor_legal_name": "Vendor",
                "invoice_reference": "I",
                "invoice_date": date(2025, 1, 1),
                "processing_date": date(2025, 1, 2),
                "currency": "AUD",
                "gross_amount": 1.0,
                "lines": [
                    {
                        "line_id": "1",
                        "line_type": "GOODS",
                        "description": "x",
                        "quantity": "1",
                        "unit_price": "1",
                        "line_total": "1",
                    }
                ],
            }
        )


@pytest.mark.parametrize(
    ("amount", "role"),
    [
        ("10000", ApprovalRole.COST_CENTRE_MANAGER),
        ("10000.01", ApprovalRole.DEPARTMENT_DIRECTOR),
        ("50000", ApprovalRole.DEPARTMENT_DIRECTOR),
        ("50000.01", ApprovalRole.EXECUTIVE_DIRECTOR),
        ("250000.01", ApprovalRole.CHIEF_FINANCIAL_OFFICER),
        ("1000000.01", ApprovalRole.CHIEF_EXECUTIVE_OFFICER),
    ],
)
def test_current_authority_boundaries(amount: str, role: ApprovalRole) -> None:
    requirement = required_authority(Decimal(amount))
    assert requirement.role is role
    assert requirement.policy_reference.version == "4.0"


def test_outcome_precedence() -> None:
    assert (
        choose_outcome(exact=True, invalid=True, escalation=True, hold=True)
        is RecommendationOutcome.REJECT_DUPLICATE
    )
    assert (
        choose_outcome(exact=False, invalid=True, escalation=True, hold=True)
        is RecommendationOutcome.REJECT_INVALID
    )
    assert (
        choose_outcome(exact=False, invalid=False, escalation=True, hold=True)
        is RecommendationOutcome.ESCALATE_CONTROL_REVIEW
    )
