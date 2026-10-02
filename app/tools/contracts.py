from datetime import datetime
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.domain.models import Currency, FinanceDecision, Money


class ToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VendorRecord(ToolModel):
    vendor_id: str
    legal_name: str
    status: str
    payment_account_last_four: str | None = None
    risk_flags: list[str]
    updated_at: datetime


class PurchaseOrderLine(ToolModel):
    line_id: str
    description: str
    quantity: Money
    unit_price: Money
    line_total: Money
    tolerance_type: str
    tolerance_absolute: Money
    tolerance_percent: Money


class GoodsReceipt(ToolModel):
    receipt_id: str
    line_id: str
    quantity_received: Money
    received_at: datetime
    source_id: str


class PurchaseOrderRecord(ToolModel):
    purchase_order_id: str
    currency: Currency
    total: Money
    approved: bool
    approval_reference: str | None = None
    lines: list[PurchaseOrderLine]
    receipts: list[GoodsReceipt]


class InvoiceHistoryMatch(ToolModel):
    stable_id: str
    invoice_reference: str
    status: str
    exact_match: bool
    fingerprint: str
    amount: Money
    currency: Currency


class EvidenceTools(Protocol):
    async def get_vendor_record(self, vendor_id: str) -> VendorRecord: ...

    async def get_purchase_order(self, purchase_order_id: str) -> PurchaseOrderRecord: ...

    async def check_invoice_history(
        self, vendor_id: str, invoice_reference: str, currency: Currency, amount: Decimal
    ) -> list[InvoiceHistoryMatch]: ...


class ConsequentialToolDenied(PermissionError):
    pass


class FinanceDecisionSubmitter(Protocol):
    async def submit(
        self, decision: FinanceDecision, *, approved: bool, idempotency_key: str
    ) -> str: ...
