import argparse
import asyncio
import json
from pathlib import Path

from pydantic import TypeAdapter

from app.domain.finance import InvoiceEvidence
from app.services.finance_controls import FinanceControlService
from app.tools.contracts import ToolOutcome
from app.tools.fixture_finance import FailurePlan, FixtureFinanceTools


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a sanitized fixture-backed control demo")
    parser.add_argument("--case", default="FIN-001")
    args = parser.parse_args()
    fixture_dir = Path("fixtures/finance")
    cases = TypeAdapter(list[InvoiceEvidence]).validate_python(
        json.loads((fixture_dir / "cases.json").read_text())
    )
    case = next((item for item in cases if item.case_id == args.case), None)
    if case is None:
        raise SystemExit(f"Unknown case: {args.case}")
    failures = (
        FailurePlan({("get_purchase_order", "PO-TIMEOUT"): ToolOutcome.TIMEOUT})
        if args.case == "FIN-004"
        else FailurePlan()
    )
    result = asyncio.run(
        FinanceControlService().evaluate(
            case, FixtureFinanceTools.from_directory(fixture_dir, failures)
        )
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
