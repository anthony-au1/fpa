from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.domain.finance import InvoiceHistoryStatus, PurchaseOrderLineType, VendorStatus
from app.domain.models import Currency, FinanceDecision, Money


class ToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    NOT_FOUND = "NOT_FOUND"
    TIMEOUT = "TIMEOUT"
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    INVALID_REQUEST = "INVALID_REQUEST"


class GetVendorRecordInput(ToolModel):
    vendor_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)


class GetPurchaseOrderInput(ToolModel):
    purchase_order_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)


class CheckInvoiceHistoryInput(ToolModel):
    vendor_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    limit: int = Field(default=50, ge=1, le=50)


class ToolCallMetadata(ToolModel):
    tool_name: str
    correlation_id: str
    outcome: ToolOutcome
    duration_ms: int = Field(ge=0)
    error_message: str | None = None


class VendorRecord(ToolModel):
    vendor_id: str
    legal_name: str
    status: VendorStatus
    payment_account_last_four: str | None = Field(default=None, pattern=r"^[0-9]{4}$")
    bank_country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    bank_details_changed_at: datetime | None = None
    bank_change_verified: bool | None = None
    first_payment_after_bank_change: bool = False
    payment_hold: bool = False
    created_at: datetime
    created_by: str
    bank_details_changed_by: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    sanctions_screen_status: str | None = None
    updated_at: datetime


class PurchaseOrderLine(ToolModel):
    line_id: str
    description: str
    line_type: PurchaseOrderLineType
    quantity: Money = Field(gt=0)
    unit_price: Money = Field(ge=0)
    line_total: Money = Field(ge=0)
    service_completed: bool | None = None


class GoodsReceipt(ToolModel):
    receipt_id: str
    line_id: str
    quantity_received: Money = Field(gt=0)
    received_at: datetime
    source_id: str


class PurchaseOrderRecord(ToolModel):
    purchase_order_id: str
    vendor_id: str
    currency: Currency
    total: Money
    tax_amount: Money = Field(default=Decimal("0"), ge=0)
    charges_amount: Money = Field(default=Decimal("0"), ge=0)
    approved: bool
    approval_reference: str | None = None
    freight_permitted: bool = False
    requires_aud_conversion: bool = False
    lines: list[PurchaseOrderLine]
    receipts: list[GoodsReceipt] = Field(default_factory=list)


class InvoiceHistoryRecord(ToolModel):
    stable_id: str
    vendor_id: str
    invoice_reference: str
    normalized_invoice_reference: str
    invoice_date: date
    status: InvoiceHistoryStatus
    amount: Money
    currency: Currency
    purchase_order_id: str | None = None
    attachment_fingerprint: str | None = None


T = TypeVar("T")


class ToolResult(ToolModel, Generic[T]):
    metadata: ToolCallMetadata
    value: T | None = None


VendorToolResult = ToolResult[VendorRecord]
PurchaseOrderToolResult = ToolResult[PurchaseOrderRecord]
InvoiceHistoryToolResult = ToolResult[list[InvoiceHistoryRecord]]


class EvidenceTools(Protocol):
    async def get_vendor_record(self, request: GetVendorRecordInput) -> VendorToolResult: ...

    async def get_purchase_order(
        self, request: GetPurchaseOrderInput
    ) -> PurchaseOrderToolResult: ...

    async def check_invoice_history(
        self, request: CheckInvoiceHistoryInput
    ) -> InvoiceHistoryToolResult: ...


class ConsequentialToolDenied(PermissionError):
    pass


class FinanceDecisionSubmitter(Protocol):
    async def submit(
        self, decision: FinanceDecision, *, approved: bool, idempotency_key: str
    ) -> str: ...
