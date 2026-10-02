from datetime import UTC, datetime
from decimal import Decimal

from app.domain.finance import (
    ApprovalRequirement,
    ApprovalRole,
    ControlCalculation,
    ControlCode,
    ControlFinding,
    ControlStatus,
    DeterministicControlResult,
    DuplicateMatchType,
    FinanceException,
    InvoiceEvidence,
    PurchaseOrderLineType,
    ToolObservation,
    VendorStatus,
)
from app.domain.models import ExceptionCategory, RecommendationOutcome, SourcedFact, Unknown
from app.services.duplicate_detection import detect_duplicates, has_blocking_exact_duplicate
from app.services.policy_rules import (
    AP_CORE,
    AUTHORITY,
    AUTHORITY_BANDS,
    BANK_CHANGE_LOOKBACK_DAYS,
    DUPLICATE,
    FRAUD,
    GOODS_ABSOLUTE_VARIANCE,
    GOODS_PERCENT_VARIANCE,
    MANUAL_PAYMENT,
    SERVICE_ABSOLUTE_VARIANCE,
    SERVICE_PERCENT_VARIANCE,
    THREE_WAY,
    VENDOR,
)
from app.tools.contracts import (
    CheckInvoiceHistoryInput,
    EvidenceTools,
    GetPurchaseOrderInput,
    GetVendorRecordInput,
    ToolOutcome,
)


def required_authority(amount_aud: Decimal) -> ApprovalRequirement:
    for limit, role in AUTHORITY_BANDS:
        if amount_aud <= limit:
            return ApprovalRequirement(
                role=role,
                authority_limit_aud=limit,
                reason="Total commitment including tax and charges",
                policy_reference=AUTHORITY,
            )
    return ApprovalRequirement(
        role=ApprovalRole.CHIEF_EXECUTIVE_OFFICER,
        authority_limit_aud=None,
        reason="Total commitment exceeds CFO limit",
        policy_reference=AUTHORITY,
    )


def choose_outcome(
    *, exact: bool, invalid: bool, escalation: bool, hold: bool
) -> RecommendationOutcome:
    if exact:
        return RecommendationOutcome.REJECT_DUPLICATE
    if invalid:
        return RecommendationOutcome.REJECT_INVALID
    if escalation:
        return RecommendationOutcome.ESCALATE_CONTROL_REVIEW
    if hold:
        return RecommendationOutcome.HOLD_FOR_INFORMATION
    return RecommendationOutcome.APPROVE_FOR_POSTING


class FinanceControlService:
    async def evaluate(
        self, invoice: InvoiceEvidence, tools: EvidenceTools
    ) -> DeterministicControlResult:
        correlation = invoice.case_id
        vendor_result = await tools.get_vendor_record(
            GetVendorRecordInput(vendor_id=invoice.vendor_id, correlation_id=correlation)
        )
        history_result = await tools.check_invoice_history(
            CheckInvoiceHistoryInput(vendor_id=invoice.vendor_id, correlation_id=correlation)
        )
        po_result = None
        if invoice.purchase_order_id:
            po_result = await tools.get_purchase_order(
                GetPurchaseOrderInput(
                    purchase_order_id=invoice.purchase_order_id, correlation_id=correlation
                )
            )

        results = [vendor_result, history_result] + ([po_result] if po_result else [])
        observations = [
            ToolObservation(
                tool_name=r.metadata.tool_name,
                correlation_id=r.metadata.correlation_id,
                outcome=r.metadata.outcome,
                duration_ms=r.metadata.duration_ms,
                error_category=r.metadata.error_message,
            )
            for r in results
        ]
        facts: list[SourcedFact] = []
        findings: list[ControlFinding] = []
        exceptions: list[FinanceException] = []
        unknowns: list[Unknown] = []
        calculations: list[ControlCalculation] = []
        approvals: list[ApprovalRequirement] = []
        now = datetime.now(UTC)

        def finding(code, status, summary, expected, observed, policy, sources=None, calcs=None):
            findings.append(
                ControlFinding(
                    finding_id=f"{invoice.case_id}:{code}:{len(findings) + 1}",
                    control=code,
                    status=status,
                    summary=summary,
                    expected=expected,
                    observed=observed,
                    source_ids=sources or [],
                    calculation_ids=calcs or [],
                    policy_reference=policy,
                )
            )

        def exception(
            category, rule, expected, observed, policy, sources=None, owner="Accounts Payable"
        ):
            exceptions.append(
                FinanceException(
                    exception_id=f"{invoice.case_id}:exception:{len(exceptions) + 1}",
                    category=category,
                    failed_rule=rule,
                    expected=expected,
                    observed=observed,
                    source_ids=sources or [],
                    responsible_owner=owner,
                    policy_reference=policy,
                )
            )

        # Vendor evidence is one control, never blanket eligibility.
        if vendor_result.metadata.outcome is ToolOutcome.SUCCESS and vendor_result.value:
            vendor = vendor_result.value
            facts.append(
                SourcedFact(
                    fact_id=f"{invoice.case_id}:vendor-status",
                    name="vendor_status",
                    value=vendor.status,
                    source_id=vendor.vendor_id,
                    source_type="get_vendor_record",
                    observed_at=now,
                )
            )
            if vendor.status is VendorStatus.ACTIVE:
                finding(
                    ControlCode.VENDOR_STATUS,
                    ControlStatus.PASS,
                    "Vendor is active",
                    "ACTIVE",
                    vendor.status,
                    VENDOR,
                    [vendor.vendor_id],
                )
            else:
                finding(
                    ControlCode.VENDOR_STATUS,
                    ControlStatus.FAIL,
                    "Vendor is not eligible",
                    "ACTIVE",
                    vendor.status,
                    VENDOR,
                    [vendor.vendor_id],
                )
                exception(
                    ExceptionCategory.VENDOR_BLOCK,
                    "Eligible vendor status",
                    "ACTIVE",
                    vendor.status,
                    VENDOR,
                    [vendor.vendor_id],
                    "Vendor Governance",
                )
            recent_bank_change = (
                vendor.bank_details_changed_at
                and (invoice.processing_date - vendor.bank_details_changed_at.date()).days
                <= BANK_CHANGE_LOOKBACK_DAYS
            )
            if recent_bank_change or vendor.bank_change_verified is False or vendor.payment_hold:
                finding(
                    ControlCode.BANK_CHANGE,
                    ControlStatus.FAIL,
                    "Bank-change controls require independent verification",
                    "Verified change and released hold",
                    "Verification or hold remains outstanding",
                    VENDOR,
                    [vendor.vendor_id],
                )
                exception(
                    ExceptionCategory.BANK_CHANGE,
                    "Independent bank-change verification",
                    "Verified by Vendor Governance",
                    "Not verified or on hold",
                    VENDOR,
                    [vendor.vendor_id],
                    "Vendor Governance",
                )
                approvals.append(
                    ApprovalRequirement(
                        role=ApprovalRole.FINANCIAL_CONTROL,
                        reason="High-risk bank-change co-approval",
                        policy_reference=VENDOR,
                    )
                )
        else:
            reason = vendor_result.metadata.outcome.value
            unknowns.append(
                Unknown(
                    unknown_id=f"{invoice.case_id}:vendor", field="vendor_record", reason=reason
                )
            )
            finding(
                ControlCode.VENDOR_STATUS,
                ControlStatus.UNKNOWN,
                "Vendor could not be verified",
                "Verified eligible vendor",
                reason,
                VENDOR,
            )

        duplicate_findings = []
        if history_result.metadata.outcome is ToolOutcome.SUCCESS:
            duplicate_findings = detect_duplicates(invoice, history_result.value or [])
            exact = has_blocking_exact_duplicate(duplicate_findings)
            probable = any(
                item.match_type is DuplicateMatchType.PROBABLE for item in duplicate_findings
            )
            finding(
                ControlCode.DUPLICATE_EXACT,
                ControlStatus.FAIL if exact else ControlStatus.PASS,
                "Exact duplicate check",
                "No paid/posted exact match",
                "Blocking exact match" if exact else "No blocking exact match",
                DUPLICATE,
                [x.matched_record_id for x in duplicate_findings],
            )
            if probable and not exact:
                finding(
                    ControlCode.DUPLICATE_PROBABLE,
                    ControlStatus.FAIL,
                    "Probable duplicate requires review",
                    "No probable match",
                    "Policy signals matched",
                    DUPLICATE,
                )
                exception(
                    ExceptionCategory.DUPLICATE_RISK,
                    "Probable duplicate review",
                    "Cleared",
                    "Outstanding",
                    DUPLICATE,
                    [x.matched_record_id for x in duplicate_findings],
                )
        else:
            unknowns.append(
                Unknown(
                    unknown_id=f"{invoice.case_id}:history",
                    field="invoice_history",
                    reason=history_result.metadata.outcome.value,
                )
            )

        # PO and three-way match.
        if not invoice.purchase_order_id:
            exception(
                ExceptionCategory.MISSING_PO,
                "PO required",
                "Approved purchase order",
                "No PO reference",
                AP_CORE,
            )
            finding(
                ControlCode.PURCHASE_ORDER,
                ControlStatus.FAIL,
                "Purchase order missing",
                "Approved PO",
                "Missing",
                AP_CORE,
            )
        elif po_result and po_result.metadata.outcome is ToolOutcome.NOT_FOUND:
            exception(
                ExceptionCategory.MISSING_PO,
                "PO required",
                "Existing approved PO",
                "PO not found",
                AP_CORE,
            )
            finding(
                ControlCode.PURCHASE_ORDER,
                ControlStatus.FAIL,
                "Purchase order not found",
                "Existing approved PO",
                "Not found",
                AP_CORE,
            )
        elif po_result and po_result.metadata.outcome is not ToolOutcome.SUCCESS:
            unknowns.append(
                Unknown(
                    unknown_id=f"{invoice.case_id}:po",
                    field="purchase_order",
                    reason=po_result.metadata.outcome.value,
                )
            )
            finding(
                ControlCode.PURCHASE_ORDER,
                ControlStatus.UNKNOWN,
                "Purchase order source unavailable",
                "Verified approved PO",
                po_result.metadata.outcome.value,
                AP_CORE,
            )
        elif po_result and po_result.value:
            po = po_result.value
            invalid_po = not po.approved or po.vendor_id != invoice.vendor_id
            finding(
                ControlCode.PURCHASE_ORDER,
                ControlStatus.FAIL if invalid_po else ControlStatus.PASS,
                "Purchase order validation",
                "Approved PO for vendor",
                f"approved={po.approved}, vendor={po.vendor_id}",
                AP_CORE,
                [po.purchase_order_id],
            )
            if po.currency != invoice.currency:
                finding(
                    ControlCode.CURRENCY,
                    ControlStatus.FAIL,
                    "Invoice and PO currencies differ",
                    po.currency,
                    invoice.currency,
                    AP_CORE,
                    [po.purchase_order_id],
                )
                exception(
                    ExceptionCategory.OTHER_CONTROL_RISK,
                    "Currency match",
                    po.currency,
                    invoice.currency,
                    AP_CORE,
                    [po.purchase_order_id],
                )
            for line in invoice.lines:
                po_line = next((item for item in po.lines if item.line_id == line.po_line_id), None)
                if not po_line:
                    exception(
                        ExceptionCategory.OTHER_CONTROL_RISK,
                        "PO line match",
                        "Existing PO line",
                        str(line.po_line_id),
                        THREE_WAY,
                        [po.purchase_order_id],
                    )
                    continue
                if line.line_type is PurchaseOrderLineType.GOODS:
                    received = sum(
                        (r.quantity_received for r in po.receipts if r.line_id == po_line.line_id),
                        Decimal("0"),
                    )
                    if received < line.quantity:
                        category = (
                            ExceptionCategory.MISSING_RECEIPT
                            if received == 0
                            else ExceptionCategory.QUANTITY_VARIANCE
                        )
                        exception(
                            category,
                            "Received quantity",
                            str(line.quantity),
                            str(received),
                            THREE_WAY,
                            [po.purchase_order_id],
                        )
                        finding(
                            ControlCode.RECEIPT,
                            ControlStatus.FAIL,
                            "Goods receipt insufficient",
                            str(line.quantity),
                            str(received),
                            THREE_WAY,
                            [po.purchase_order_id],
                        )
                    absolute, percent = GOODS_ABSOLUTE_VARIANCE, GOODS_PERCENT_VARIANCE
                else:
                    if po_line.service_completed is not True:
                        exception(
                            ExceptionCategory.MISSING_RECEIPT,
                            "Service completion",
                            "Recorded completion",
                            "Missing",
                            THREE_WAY,
                            [po.purchase_order_id],
                        )
                        finding(
                            ControlCode.RECEIPT,
                            ControlStatus.FAIL,
                            "Service completion missing",
                            "Recorded completion",
                            "Missing",
                            THREE_WAY,
                            [po.purchase_order_id],
                        )
                    absolute, percent = SERVICE_ABSOLUTE_VARIANCE, SERVICE_PERCENT_VARIANCE
                variance = abs(line.line_total - po_line.line_total)
                allowed = min(absolute, po_line.line_total * percent)
                calc_id = f"{invoice.case_id}:variance:{line.line_id}"
                calculations.append(
                    ControlCalculation(
                        calculation_id=calc_id,
                        rule_id="LOWER_OF_ABSOLUTE_OR_PERCENT",
                        inputs={
                            "invoice_line_total": line.line_total,
                            "po_line_total": po_line.line_total,
                            "absolute_cap": absolute,
                            "percentage": percent,
                        },
                        formula="abs(invoice-po) <= min(absolute cap, po value * percentage)",
                        result=variance,
                        allowed_threshold=allowed,
                        currency=invoice.currency,
                        source_ids=[po.purchase_order_id],
                        policy_reference=THREE_WAY,
                    )
                )
                if variance > allowed:
                    exception(
                        ExceptionCategory.PRICE_VARIANCE,
                        "Line value tolerance",
                        f"<= {allowed}",
                        str(variance),
                        THREE_WAY,
                        [po.purchase_order_id],
                    )
                    finding(
                        ControlCode.THREE_WAY_MATCH,
                        ControlStatus.FAIL,
                        "Line variance exceeds tolerance",
                        f"<= {allowed}",
                        str(variance),
                        THREE_WAY,
                        [po.purchase_order_id],
                        [calc_id],
                    )

        # Current-policy authority constants are application rules; RAG cannot alter them.
        if invoice.currency == "AUD":
            approvals.insert(0, required_authority(invoice.gross_amount))
            finding(
                ControlCode.AUTHORITY,
                ControlStatus.PASS,
                "Current authority band identified",
                "Current FIN-POL-003 v6.0 band",
                approvals[0].role,
                AUTHORITY,
            )
        elif invoice.fx_rate and invoice.fx_rate.to_currency == "AUD":
            approvals.insert(0, required_authority(invoice.gross_amount * invoice.fx_rate.rate))
        else:
            unknowns.append(
                Unknown(
                    unknown_id=f"{invoice.case_id}:fx",
                    field="corporate_fx_rate",
                    reason="No sourced corporate AUD rate/date",
                )
            )
            finding(
                ControlCode.AUTHORITY,
                ControlStatus.UNKNOWN,
                "AUD authority cannot be calculated",
                "Sourced corporate FX rate",
                "Missing",
                AUTHORITY,
            )

        high_risk = bool(invoice.risk_indicators) or invoice.payment_type.value != "STANDARD"
        if high_risk:
            finding(
                ControlCode.HIGH_RISK,
                ControlStatus.FAIL,
                "High-risk indicators require review",
                "No unresolved high-risk indicators",
                ",".join(sorted(x.value for x in invoice.risk_indicators)) or invoice.payment_type,
                FRAUD,
            )
            approvals.append(
                ApprovalRequirement(
                    role=ApprovalRole.FINANCIAL_CONTROL,
                    reason="High-risk control review",
                    policy_reference=MANUAL_PAYMENT
                    if invoice.payment_type.value != "STANDARD"
                    else FRAUD,
                )
            )
        if (
            invoice.actors.requester_personal_benefit is True
            and invoice.actors.requester_id == invoice.actors.financial_approver_id
        ):
            finding(
                ControlCode.SEGREGATION_OF_DUTIES,
                ControlStatus.FAIL,
                "Self-approval is prohibited",
                "Distinct requester and approver",
                "Same identity",
                AUTHORITY,
            )
            exception(
                ExceptionCategory.AUTHORITY_GAP,
                "Segregation of duties",
                "Distinct identities",
                "Same identity",
                AUTHORITY,
            )

        exact = has_blocking_exact_duplicate(duplicate_findings)
        invalid = any(e.category == ExceptionCategory.VENDOR_BLOCK for e in exceptions)
        escalation = high_risk or any(
            e.category in {ExceptionCategory.BANK_CHANGE, ExceptionCategory.AUTHORITY_GAP}
            for e in exceptions
        )
        hold = bool(
            exceptions or unknowns or any(f.status is not ControlStatus.PASS for f in findings)
        )
        outcome = choose_outcome(exact=exact, invalid=invalid, escalation=escalation, hold=hold)
        return DeterministicControlResult(
            case_id=invoice.case_id,
            sourced_facts=facts,
            calculations=calculations,
            findings=findings,
            exceptions=exceptions,
            unknowns=unknowns,
            duplicate_findings=duplicate_findings,
            required_approvals=approvals,
            tool_observations=observations,
            outcome_candidate=outcome,
            eligible_for_approval=outcome is RecommendationOutcome.APPROVE_FOR_POSTING,
        )
