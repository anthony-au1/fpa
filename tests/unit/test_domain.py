from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.models import FinancialCase, RunStatus
from app.domain.transitions import InvalidStateTransition, validate_transition


def test_money_is_decimal_and_serializes_as_string(case_payload: dict) -> None:
    financial_case = FinancialCase.model_validate(case_payload)
    assert financial_case.amount == Decimal("100.10")
    assert financial_case.model_dump(mode="json")["amount"] == "100.10"


def test_float_money_is_rejected_by_financial_boundary() -> None:
    # Binary floats must not cross into financial arithmetic unnoticed.
    with pytest.raises(ValidationError):
        FinancialCase.model_validate(
            {
                "case_id": "C",
                "invoice_reference": "I",
                "vendor": "V",
                "amount": 0.1,
                "currency": "AUD",
            }
        )


def test_currency_is_validated(case_payload: dict) -> None:
    case_payload["currency"] = "aud"
    with pytest.raises(ValidationError):
        FinancialCase.model_validate(case_payload)


def test_state_transition_rules() -> None:
    validate_transition(RunStatus.CREATED, RunStatus.RUNNING)
    validate_transition(RunStatus.WAITING_FOR_APPROVAL, RunStatus.COMPLETE)
    with pytest.raises(InvalidStateTransition):
        validate_transition(RunStatus.COMPLETE, RunStatus.RUNNING)
