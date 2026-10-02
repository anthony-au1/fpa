import asyncio
from pathlib import Path

from app.tools.contracts import GetPurchaseOrderInput, GetVendorRecordInput, ToolOutcome
from app.tools.fixture_finance import FailurePlan, FixtureFinanceTools

FIXTURES = Path("fixtures/finance")


def test_fixture_tools_distinguish_not_found_and_timeout() -> None:
    tools = FixtureFinanceTools.from_directory(
        FIXTURES, FailurePlan({("get_purchase_order", "PO-TIMEOUT"): ToolOutcome.TIMEOUT})
    )
    missing = asyncio.run(
        tools.get_vendor_record(GetVendorRecordInput(vendor_id="NOPE", correlation_id="run-1"))
    )
    timeout = asyncio.run(
        tools.get_purchase_order(
            GetPurchaseOrderInput(purchase_order_id="PO-TIMEOUT", correlation_id="run-1")
        )
    )
    assert missing.metadata.outcome is ToolOutcome.NOT_FOUND
    assert timeout.metadata.outcome is ToolOutcome.TIMEOUT
    assert missing.value is None and timeout.value is None


def test_tool_observation_is_redacted() -> None:
    tools = FixtureFinanceTools.from_directory(FIXTURES)
    result = asyncio.run(
        tools.get_vendor_record(GetVendorRecordInput(vendor_id="VEND-001", correlation_id="run-1"))
    )
    serialized = result.metadata.model_dump_json()
    assert "1234" not in serialized
    assert result.metadata.tool_name == "get_vendor_record"
