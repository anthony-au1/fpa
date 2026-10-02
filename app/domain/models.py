from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
)

Currency = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


def reject_float(value: object) -> object:
    if isinstance(value, float):
        raise ValueError("Financial values must use Decimal-compatible strings, not float")
    return value


Money = Annotated[Decimal, BeforeValidator(reject_float)]


def utc_now() -> datetime:
    return datetime.now(UTC)


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class RecommendationOutcome(StrEnum):
    APPROVE_FOR_POSTING = "APPROVE_FOR_POSTING"
    HOLD_FOR_INFORMATION = "HOLD_FOR_INFORMATION"
    REJECT_DUPLICATE = "REJECT_DUPLICATE"
    REJECT_INVALID = "REJECT_INVALID"
    ESCALATE_CONTROL_REVIEW = "ESCALATE_CONTROL_REVIEW"


class ApprovalDecisionValue(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DocumentAuthority(StrEnum):
    CURRENT = "current"
    SUPERSEDED = "superseded"
    UNTRUSTED = "untrusted"


class ExceptionCategory(StrEnum):
    MISSING_PO = "MISSING_PO"
    MISSING_RECEIPT = "MISSING_RECEIPT"
    PRICE_VARIANCE = "PRICE_VARIANCE"
    QUANTITY_VARIANCE = "QUANTITY_VARIANCE"
    DUPLICATE_RISK = "DUPLICATE_RISK"
    VENDOR_BLOCK = "VENDOR_BLOCK"
    BANK_CHANGE = "BANK_CHANGE"
    AUTHORITY_GAP = "AUTHORITY_GAP"
    TAX_QUERY = "TAX_QUERY"
    OTHER_CONTROL_RISK = "OTHER_CONTROL_RISK"


class FinancialCase(DomainModel):
    case_id: str = Field(min_length=1, max_length=100)
    invoice_reference: str = Field(min_length=1, max_length=200)
    vendor: str = Field(min_length=1, max_length=300)
    amount: Money
    currency: Currency
    invoice_date: date | None = None
    tax_amount: Money | None = None
    purchase_order_reference: str | None = None
    notes: str | None = Field(default=None, max_length=4000)
    attachment_ids: list[str] = Field(default_factory=list)

    @field_serializer("amount", "tax_amount", when_used="json")
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        return None if value is None else str(value)


class Citation(DomainModel):
    document_id: str
    version: str | None = None
    section: str | None = None
    chunk_id: str | None = None


class RetrievedDocument(DomainModel):
    document_id: str
    title: str
    version: str | None = None
    authority: DocumentAuthority
    chunk_id: str
    heading: str | None = None
    content: str
    relevance: Decimal = Field(ge=0)
    citation: Citation


class SourcedFact(DomainModel):
    fact_id: str
    name: str
    value: str | int | bool | Decimal | date | datetime
    source_id: str
    source_type: str
    observed_at: datetime


class Calculation(DomainModel):
    calculation_id: str
    formula: str
    inputs: dict[str, Money]
    result: Money
    currency: Currency | None = None
    rounding_method: str
    source_fact_ids: list[str] = Field(default_factory=list)


class PolicyFinding(DomainModel):
    finding_id: str
    rule: str
    explanation: str
    citations: list[Citation] = Field(min_length=1)
    source_fact_ids: list[str] = Field(default_factory=list)


class ExceptionFinding(DomainModel):
    exception_id: str
    category: ExceptionCategory
    failed_rule: str
    expected: str
    observed: str
    citations: list[Citation]
    responsible_owner: str
    next_review_date: date | None = None


class Unknown(DomainModel):
    unknown_id: str
    field: str
    reason: str
    required_to_proceed: bool = True


class Recommendation(DomainModel):
    outcome: RecommendationOutcome
    summary: str
    confidence: Decimal = Field(ge=0, le=1)
    sourced_fact_ids: list[str] = Field(default_factory=list)
    calculation_ids: list[str] = Field(default_factory=list)
    policy_finding_ids: list[str] = Field(default_factory=list)
    exception_ids: list[str] = Field(default_factory=list)
    unknown_ids: list[str] = Field(default_factory=list)
    next_action: str


class ApprovalRequest(DomainModel):
    approval_request_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    status: ApprovalStatus = ApprovalStatus.PENDING
    idempotency_key: str
    recommendation: Recommendation
    requested_at: datetime = Field(default_factory=utc_now)


class ApprovalDecision(DomainModel):
    decision: ApprovalDecisionValue
    approver_id: str
    approver_role: str
    comment: str | None = Field(default=None, max_length=2000)
    idempotency_key: str = Field(min_length=1, max_length=200)
    decided_at: datetime = Field(default_factory=utc_now)


class FinanceDecision(DomainModel):
    finance_decision_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    recommendation_outcome: RecommendationOutcome
    idempotency_key: str
    external_reference: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class AuditEvent(DomainModel):
    event_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    sequence: int = Field(ge=1)
    event_type: str
    actor_type: str
    actor_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class Run(DomainModel):
    run_id: UUID
    financial_case: FinancialCase
    status: RunStatus
    current_node: str | None = None
    step_count: int = Field(default=0, ge=0)
    tool_call_count: int = Field(default=0, ge=0)
    recommendation: Recommendation | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
