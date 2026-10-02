import json
from collections.abc import Mapping
from pathlib import Path
from time import perf_counter_ns

from pydantic import TypeAdapter, ValidationError

from app.tools.contracts import (
    CheckInvoiceHistoryInput,
    GetPurchaseOrderInput,
    GetVendorRecordInput,
    InvoiceHistoryRecord,
    InvoiceHistoryToolResult,
    PurchaseOrderRecord,
    PurchaseOrderToolResult,
    ToolCallMetadata,
    ToolOutcome,
    VendorRecord,
    VendorToolResult,
)


class FixtureDataError(ValueError):
    """A reviewable local integration fixture is malformed."""


class FailurePlan:
    def __init__(self, failures: Mapping[tuple[str, str], ToolOutcome] | None = None) -> None:
        self._failures = dict(failures or {})

    def outcome_for(self, tool_name: str, key: str) -> ToolOutcome | None:
        return self._failures.get((tool_name, key))


class FixtureFinanceTools:
    """Deterministic, read-only simulation of upstream finance systems."""

    def __init__(self, vendors, purchase_orders, invoice_history, failure_plan=None) -> None:
        self._vendors = {item.vendor_id: item for item in vendors}
        self._purchase_orders = {item.purchase_order_id: item for item in purchase_orders}
        self._history = tuple(invoice_history)
        self._failure_plan = failure_plan or FailurePlan()

    @classmethod
    def from_directory(cls, directory: Path, failure_plan=None) -> "FixtureFinanceTools":
        try:
            vendors = TypeAdapter(list[VendorRecord]).validate_python(
                json.loads((directory / "vendors.json").read_text())
            )
            purchase_orders = TypeAdapter(list[PurchaseOrderRecord]).validate_python(
                json.loads((directory / "purchase_orders.json").read_text())
            )
            history = TypeAdapter(list[InvoiceHistoryRecord]).validate_python(
                json.loads((directory / "invoice_history.json").read_text())
            )
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise FixtureDataError(f"Invalid finance fixture in {directory}: {exc}") from exc
        return cls(vendors, purchase_orders, history, failure_plan)

    def _metadata(self, name, correlation_id, outcome, started) -> ToolCallMetadata:
        message = None if outcome in {ToolOutcome.SUCCESS, ToolOutcome.NOT_FOUND} else outcome.value
        return ToolCallMetadata(
            tool_name=name,
            correlation_id=correlation_id,
            outcome=outcome,
            duration_ms=max(0, (perf_counter_ns() - started) // 1_000_000),
            error_message=message,
        )

    async def get_vendor_record(self, request: GetVendorRecordInput) -> VendorToolResult:
        started, name = perf_counter_ns(), "get_vendor_record"
        forced = self._failure_plan.outcome_for(name, request.vendor_id)
        if forced:
            return VendorToolResult(
                metadata=self._metadata(name, request.correlation_id, forced, started)
            )
        value = self._vendors.get(request.vendor_id)
        outcome = ToolOutcome.SUCCESS if value else ToolOutcome.NOT_FOUND
        return VendorToolResult(
            metadata=self._metadata(name, request.correlation_id, outcome, started), value=value
        )

    async def get_purchase_order(self, request: GetPurchaseOrderInput) -> PurchaseOrderToolResult:
        started, name = perf_counter_ns(), "get_purchase_order"
        forced = self._failure_plan.outcome_for(name, request.purchase_order_id)
        if forced:
            return PurchaseOrderToolResult(
                metadata=self._metadata(name, request.correlation_id, forced, started)
            )
        value = self._purchase_orders.get(request.purchase_order_id)
        outcome = ToolOutcome.SUCCESS if value else ToolOutcome.NOT_FOUND
        return PurchaseOrderToolResult(
            metadata=self._metadata(name, request.correlation_id, outcome, started), value=value
        )

    async def check_invoice_history(
        self, request: CheckInvoiceHistoryInput
    ) -> InvoiceHistoryToolResult:
        started, name = perf_counter_ns(), "check_invoice_history"
        forced = self._failure_plan.outcome_for(name, request.vendor_id)
        if forced:
            return InvoiceHistoryToolResult(
                metadata=self._metadata(name, request.correlation_id, forced, started)
            )
        records = sorted(
            (item for item in self._history if item.vendor_id == request.vendor_id),
            key=lambda item: item.stable_id,
        )[: request.limit]
        return InvoiceHistoryToolResult(
            metadata=self._metadata(name, request.correlation_id, ToolOutcome.SUCCESS, started),
            value=records,
        )
