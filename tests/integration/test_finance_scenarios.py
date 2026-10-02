import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import TypeAdapter

from app.domain.finance import ApprovalRole, ControlStatus, DuplicateMatchType, InvoiceEvidence
from app.domain.models import ExceptionCategory, RecommendationOutcome
from app.services.finance_controls import FinanceControlService
from app.tools.contracts import (
    InvoiceHistoryRecord,
    PurchaseOrderRecord,
    ToolOutcome,
    VendorRecord,
)
from app.tools.fixture_finance import FailurePlan, FixtureFinanceTools

FIXTURES = Path("fixtures/finance")


def load_cases() -> dict[str, InvoiceEvidence]:
    cases = TypeAdapter(list[InvoiceEvidence]).validate_python(
        json.loads((FIXTURES / "cases.json").read_text())
    )
    return {case.case_id: case for case in cases}


def run(case, tools=None):
    return asyncio.run(
        FinanceControlService().evaluate(
            case, tools or FixtureFinanceTools.from_directory(FIXTURES)
        )
    )


def changed(case: InvoiceEvidence, **updates) -> InvoiceEvidence:
    data = case.model_dump(mode="json")
    data.update(updates)
    return InvoiceEvidence.model_validate(data)


def tools_with_vendor(vendor: VendorRecord) -> FixtureFinanceTools:
    vendors = TypeAdapter(list[VendorRecord]).validate_python(
        json.loads((FIXTURES / "vendors.json").read_text())
    )
    vendors = [vendor if item.vendor_id == vendor.vendor_id else item for item in vendors]
    purchase_orders = TypeAdapter(list[PurchaseOrderRecord]).validate_python(
        json.loads((FIXTURES / "purchase_orders.json").read_text())
    )
    history = TypeAdapter(list[InvoiceHistoryRecord]).validate_python(
        json.loads((FIXTURES / "invoice_history.json").read_text())
    )
    return FixtureFinanceTools(vendors, purchase_orders, history)


def vendor_one() -> VendorRecord:
    return TypeAdapter(list[VendorRecord]).validate_python(
        json.loads((FIXTURES / "vendors.json").read_text())
    )[0]


def test_fin_001_valid_evidence_passes_without_submission() -> None:
    result = run(load_cases()["FIN-001"])
    assert result.outcome_candidate is RecommendationOutcome.APPROVE_FOR_POSTING
    assert result.eligible_for_approval
    assert result.requires_human_approval
    assert "not authorization" in result.authorization_notice


def test_fin_002_exact_paid_duplicate_is_rejected_with_stable_evidence() -> None:
    result = run(load_cases()["FIN-002"])
    assert result.outcome_candidate is RecommendationOutcome.REJECT_DUPLICATE
    assert any(
        x.match_type is DuplicateMatchType.EXACT and x.matched_record_id == "HIST-PAID-001"
        for x in result.duplicate_findings
    )
    assert not result.eligible_for_approval


def test_probable_duplicate_holds_instead_of_rejecting() -> None:
    case = changed(
        load_cases()["FIN-001"],
        invoice_reference="ABC.123",
        gross_amount="1000",
        tax_amount="0",
        purchase_order_id="PO-SERVICE",
        lines=[
            {
                "line_id": "1",
                "po_line_id": "S1",
                "line_type": "SERVICE",
                "description": "Consulting",
                "quantity": "1",
                "unit_price": "1000",
                "line_total": "1000",
            }
        ],
    )
    result = run(case)
    assert any(x.match_type is DuplicateMatchType.PROBABLE for x in result.duplicate_findings)
    assert result.outcome_candidate is RecommendationOutcome.HOLD_FOR_INFORMATION


def test_fin_003_untrusted_notes_cannot_bypass_bank_controls() -> None:
    result = run(load_cases()["FIN-003"])
    assert result.outcome_candidate is RecommendationOutcome.ESCALATE_CONTROL_REVIEW
    assert any(x.category == ExceptionCategory.BANK_CHANGE for x in result.exceptions)
    assert {ApprovalRole.TREASURY, ApprovalRole.FINANCIAL_CONTROL}.issubset(
        {requirement.role for requirement in result.required_approvals}
    )
    assert not result.eligible_for_approval


def test_fin_004_timeout_is_unknown_not_missing_po() -> None:
    tools = FixtureFinanceTools.from_directory(
        FIXTURES, FailurePlan({("get_purchase_order", "PO-TIMEOUT"): ToolOutcome.TIMEOUT})
    )
    result = run(load_cases()["FIN-004"], tools)
    assert any(x.field == "purchase_order" and x.reason == "TIMEOUT" for x in result.unknowns)
    assert not any(x.category == ExceptionCategory.MISSING_PO for x in result.exceptions)
    assert result.outcome_candidate is RecommendationOutcome.HOLD_FOR_INFORMATION


def test_missing_receipt_is_explicit_and_blocks() -> None:
    case = changed(load_cases()["FIN-004"], purchase_order_id="PO-NORECEIPT")
    result = run(case)
    assert any(x.category == ExceptionCategory.MISSING_RECEIPT for x in result.exceptions)
    assert any(x.status is ControlStatus.FAIL for x in result.findings)
    assert not result.eligible_for_approval


def test_transient_history_failure_remains_unknown() -> None:
    tools = FixtureFinanceTools.from_directory(
        FIXTURES,
        FailurePlan({("check_invoice_history", "VEND-001"): ToolOutcome.TRANSIENT_FAILURE}),
    )
    result = run(load_cases()["FIN-001"], tools)
    assert any(
        x.field == "invoice_history" and x.reason == "TRANSIENT_FAILURE" for x in result.unknowns
    )
    assert result.outcome_candidate is RecommendationOutcome.HOLD_FOR_INFORMATION


def test_missing_po_is_business_failure() -> None:
    result = run(changed(load_cases()["FIN-004"], purchase_order_id="PO-NOT-FOUND"))
    assert any(x.category == ExceptionCategory.MISSING_PO for x in result.exceptions)
    assert not any(x.field == "purchase_order" for x in result.unknowns)


def test_goods_quantity_above_receipt_fails() -> None:
    case = changed(
        load_cases()["FIN-001"],
        gross_amount="1200",
        tax_amount="0",
        lines=[
            {
                "line_id": "1",
                "po_line_id": "1",
                "line_type": "GOODS",
                "description": "Widgets",
                "quantity": "12",
                "unit_price": "100",
                "line_total": "1200",
            }
        ],
    )
    result = run(case)
    assert any(x.category == ExceptionCategory.QUANTITY_VARIANCE for x in result.exceptions)


def test_goods_price_variance_outside_lower_of_tolerance_fails() -> None:
    case = changed(
        load_cases()["FIN-001"],
        gross_amount="1020",
        tax_amount="0",
        lines=[
            {
                "line_id": "1",
                "po_line_id": "1",
                "line_type": "GOODS",
                "description": "Widgets",
                "quantity": "10",
                "unit_price": "102",
                "line_total": "1020",
            }
        ],
    )
    result = run(case)
    assert any(x.category == ExceptionCategory.PRICE_VARIANCE for x in result.exceptions)
    assert result.calculations[0].allowed_threshold == 10


def test_service_inside_tolerance_passes_reconciliation() -> None:
    case = changed(
        load_cases()["FIN-001"],
        invoice_reference="SERVICE-NEW",
        gross_amount="1010",
        tax_amount="0",
        purchase_order_id="PO-SERVICE",
        lines=[
            {
                "line_id": "1",
                "po_line_id": "S1",
                "line_type": "SERVICE",
                "description": "Consulting",
                "quantity": "1",
                "unit_price": "1010",
                "line_total": "1010",
            }
        ],
    )
    result = run(case)
    assert not any(
        x.category in {ExceptionCategory.PRICE_VARIANCE, ExceptionCategory.MISSING_RECEIPT}
        for x in result.exceptions
    )


def test_currency_mismatch_is_structured() -> None:
    case = changed(load_cases()["FIN-001"], currency="USD")
    result = run(case)
    assert any(
        x.control.value == "CURRENCY" and x.status is ControlStatus.FAIL for x in result.findings
    )
    assert any(x.field == "corporate_fx_rate" for x in result.unknowns)
    currency_finding = next(x for x in result.findings if x.control.value == "CURRENCY")
    assert (
        currency_finding.policy_reference.document_id,
        currency_finding.policy_reference.version,
    ) == (
        "FIN-POL-009",
        "1.6",
    )


def test_fraud_escalation_requires_two_indicators() -> None:
    one = run(changed(load_cases()["FIN-001"], risk_indicators=["URGENT_OR_SECRET_LANGUAGE"]))
    two = run(
        changed(
            load_cases()["FIN-001"],
            risk_indicators=["URGENT_OR_SECRET_LANGUAGE", "BYPASS_APPROVAL_REQUEST"],
        )
    )
    assert one.outcome_candidate is RecommendationOutcome.APPROVE_FOR_POSTING
    assert two.outcome_candidate is RecommendationOutcome.ESCALATE_CONTROL_REVIEW
    fraud = next(x for x in two.findings if x.control.value == "HIGH_RISK")
    assert (fraud.policy_reference.document_id, fraud.policy_reference.version) == (
        "FIN-POL-005",
        "2.8",
    )


def test_new_vendor_rule_is_strictly_less_than_30_days() -> None:
    case = load_cases()["FIN-001"]
    base = vendor_one()
    processing = datetime.combine(
        case.processing_date, datetime.min.time(), tzinfo=base.created_at.tzinfo
    )
    day_29 = run(
        case,
        tools_with_vendor(base.model_copy(update={"created_at": processing - timedelta(days=29)})),
    )
    day_30 = run(
        case,
        tools_with_vendor(base.model_copy(update={"created_at": processing - timedelta(days=30)})),
    )
    assert day_29.outcome_candidate is RecommendationOutcome.ESCALATE_CONTROL_REVIEW
    assert day_30.outcome_candidate is RecommendationOutcome.APPROVE_FOR_POSTING


def test_bank_change_uses_control_state_not_generic_recency() -> None:
    case = load_cases()["FIN-001"]
    base = vendor_one().model_copy(
        update={
            "bank_details_changed_at": datetime(2020, 1, 1, tzinfo=vendor_one().created_at.tzinfo),
            "bank_change_verified": True,
            "payment_hold": False,
        }
    )
    historical = run(case, tools_with_vendor(base))
    first_payment = run(
        case, tools_with_vendor(base.model_copy(update={"first_payment_after_bank_change": True}))
    )
    assert not any(x.category == ExceptionCategory.BANK_CHANGE for x in historical.exceptions)
    assert any(x.category == ExceptionCategory.BANK_CHANGE for x in first_payment.exceptions)


def test_emitted_control_references_are_never_superseded() -> None:
    results = [run(load_cases()[case_id]) for case_id in ("FIN-001", "FIN-002", "FIN-003")]
    references = []
    for result in results:
        references.extend(item.policy_reference for item in result.findings)
        references.extend(item.policy_reference for item in result.exceptions)
        references.extend(item.policy_reference for item in result.calculations)
        references.extend(item.policy_reference for item in result.required_approvals)
    assert references
    assert all(reference.document_id != "FIN-POL-003-OLD" for reference in references)
    assert all(
        (reference.document_id, reference.version) != ("FIN-POL-003", "1.0")
        for reference in references
    )
