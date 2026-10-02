from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, model_validator

from app.domain.models import (
    Currency,
    DomainModel,
    Money,
    RecommendationOutcome,
    SourcedFact,
    Unknown,
)


class VendorStatus(StrEnum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    DORMANT = "DORMANT"
    SANCTIONS_REVIEW = "SANCTIONS_REVIEW"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class InvoiceHistoryStatus(StrEnum):
    PAID = "PAID"
    POSTED = "POSTED"
    HELD = "HELD"
    REJECTED = "REJECTED"


class PurchaseOrderLineType(StrEnum):
    GOODS = "GOODS"
    SERVICE = "SERVICE"


class PaymentType(StrEnum):
    STANDARD = "STANDARD"
    MANUAL = "MANUAL"
    SAME_DAY = "SAME_DAY"


class FraudIndicator(StrEnum):
    BANK_DETAILS_CHANGED = "BANK_DETAILS_CHANGED"
    URGENT_OR_SECRET_LANGUAGE = "URGENT_OR_SECRET_LANGUAGE"
    UNUSUAL_DOMAIN = "UNUSUAL_DOMAIN"
    VENDOR_NAME_MISMATCH = "VENDOR_NAME_MISMATCH"
    NEW_PAYMENT_COUNTRY = "NEW_PAYMENT_COUNTRY"
    WEEKEND_MANUAL_PAYMENT = "WEEKEND_MANUAL_PAYMENT"
    REPEATED_ROUND_DOLLAR_INVOICES = "REPEATED_ROUND_DOLLAR_INVOICES"
    BYPASS_APPROVAL_REQUEST = "BYPASS_APPROVAL_REQUEST"


class ControlStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class ControlCode(StrEnum):
    VENDOR_STATUS = "VENDOR_STATUS"
    DUPLICATE_EXACT = "DUPLICATE_EXACT"
    DUPLICATE_PROBABLE = "DUPLICATE_PROBABLE"
    PURCHASE_ORDER = "PURCHASE_ORDER"
    CURRENCY = "CURRENCY"
    RECEIPT = "RECEIPT"
    THREE_WAY_MATCH = "THREE_WAY_MATCH"
    BANK_CHANGE = "BANK_CHANGE"
    HIGH_RISK = "HIGH_RISK"
    AUTHORITY = "AUTHORITY"
    SEGREGATION_OF_DUTIES = "SEGREGATION_OF_DUTIES"


class DuplicateMatchType(StrEnum):
    EXACT = "EXACT"
    PROBABLE = "PROBABLE"


class ApprovalRole(StrEnum):
    COST_CENTRE_MANAGER = "Cost Centre Manager"
    DEPARTMENT_DIRECTOR = "Department Director"
    EXECUTIVE_DIRECTOR = "Executive Director"
    CHIEF_FINANCIAL_OFFICER = "Chief Financial Officer"
    CHIEF_EXECUTIVE_OFFICER = "Chief Executive Officer"
    FINANCIAL_CONTROL = "Financial Control"
    TREASURY = "Treasury"


class InvoiceLine(DomainModel):
    line_id: str
    po_line_id: str | None = None
    line_type: PurchaseOrderLineType
    description: str
    quantity: Money = Field(gt=0)
    unit_price: Money = Field(ge=0)
    line_total: Money = Field(ge=0)

    @model_validator(mode="after")
    def validate_total(self) -> "InvoiceLine":
        if self.quantity * self.unit_price != self.line_total:
            raise ValueError("line_total must equal quantity multiplied by unit_price")
        return self


class FxRateEvidence(DomainModel):
    from_currency: Currency
    to_currency: Currency = "AUD"
    rate: Money = Field(gt=0)
    rate_date: date
    source_id: str


class ActorEvidence(DomainModel):
    requester_id: str | None = None
    financial_approver_id: str | None = None
    requester_personal_benefit: bool | None = None


class InvoiceEvidence(DomainModel):
    case_id: str
    vendor_id: str
    vendor_legal_name: str
    invoice_reference: str
    invoice_date: date
    processing_date: date
    currency: Currency
    gross_amount: Money = Field(gt=0)
    tax_amount: Money = Field(default=Decimal("0"), ge=0)
    charges_amount: Money = Field(default=Decimal("0"), ge=0)
    lines: list[InvoiceLine] = Field(min_length=1)
    purchase_order_id: str | None = None
    attachment_fingerprint: str | None = None
    payment_type: PaymentType = PaymentType.STANDARD
    risk_indicators: set[FraudIndicator] = Field(default_factory=set)
    actors: ActorEvidence = Field(default_factory=ActorEvidence)
    notes: str | None = None
    fx_rate: FxRateEvidence | None = None

    @model_validator(mode="after")
    def validate_gross_total(self) -> "InvoiceEvidence":
        expected = sum((line.line_total for line in self.lines), start=0)
        expected += self.tax_amount + self.charges_amount
        if expected != self.gross_amount:
            raise ValueError("gross_amount must equal lines plus tax and charges")
        return self


class PolicyReference(DomainModel):
    document_id: str
    version: str
    section: str
    rule_id: str


class ControlCalculation(DomainModel):
    calculation_id: str
    rule_id: str
    inputs: dict[str, Money]
    formula: str
    result: Money
    allowed_threshold: Money | None = None
    currency: Currency | None = None
    rounding_method: str = "exact Decimal arithmetic; no rounding"
    source_ids: list[str] = Field(default_factory=list)
    policy_reference: PolicyReference


class ControlFinding(DomainModel):
    finding_id: str
    control: ControlCode
    status: ControlStatus
    summary: str
    expected: str
    observed: str
    source_ids: list[str] = Field(default_factory=list)
    calculation_ids: list[str] = Field(default_factory=list)
    policy_reference: PolicyReference


class FinanceException(DomainModel):
    exception_id: str
    category: str
    failed_rule: str
    expected: str
    observed: str
    source_ids: list[str]
    responsible_owner: str
    policy_reference: PolicyReference


class DuplicateFinding(DomainModel):
    match_type: DuplicateMatchType
    matched_record_id: str
    history_status: InvoiceHistoryStatus
    matched_fields: list[str]
    signals: list[str]


class ApprovalRequirement(DomainModel):
    role: ApprovalRole
    authority_limit_aud: Money | None = None
    reason: str
    policy_reference: PolicyReference


class ToolObservation(DomainModel):
    tool_name: str
    correlation_id: str
    outcome: str
    duration_ms: int = Field(ge=0)
    error_category: str | None = None


class DeterministicControlResult(DomainModel):
    case_id: str
    sourced_facts: list[SourcedFact]
    calculations: list[ControlCalculation]
    findings: list[ControlFinding]
    exceptions: list[FinanceException]
    unknowns: list[Unknown]
    duplicate_findings: list[DuplicateFinding]
    required_approvals: list[ApprovalRequirement]
    tool_observations: list[ToolObservation]
    outcome_candidate: RecommendationOutcome
    eligible_for_approval: bool
    requires_human_approval: bool = True
    authorization_notice: str = (
        "This deterministic result is not authorization to post, pay, or change finance data."
    )
