from app.domain.workflow import EvidenceBundle
from app.tools.contracts import (
    CheckInvoiceHistoryInput,
    GetPurchaseOrderInput,
    GetVendorRecordInput,
    InvoiceHistoryToolResult,
    PurchaseOrderToolResult,
    VendorToolResult,
)


class GatheredEvidenceTools:
    """Feeds already-gathered evidence into deterministic Task 3 controls."""

    def __init__(self, bundle: EvidenceBundle) -> None:
        self.bundle = bundle

    async def get_vendor_record(self, request: GetVendorRecordInput) -> VendorToolResult:
        del request
        return self.bundle.vendor

    async def get_purchase_order(self, request: GetPurchaseOrderInput) -> PurchaseOrderToolResult:
        del request
        if self.bundle.purchase_order is None:
            raise RuntimeError("Purchase-order evidence was not gathered")
        return self.bundle.purchase_order

    async def check_invoice_history(
        self, request: CheckInvoiceHistoryInput
    ) -> InvoiceHistoryToolResult:
        del request
        return self.bundle.invoice_history
