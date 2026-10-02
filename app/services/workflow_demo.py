from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.config import Settings
from app.llm.provider import FakeModelProvider
from app.main import create_app


def main() -> None:
    analysis = {
        "sourced_findings": [],
        "policy_findings": [],
        "inferences": [],
        "unknowns": [],
        "explanation": "The deterministic controls passed and current policy requires approval.",
        "confidence": "0.90",
    }
    case = {
        "case_id": "FIN-001",
        "invoice_reference": "INV-001",
        "vendor": "Acme Supplies Pty Ltd",
        "amount": "1100",
        "currency": "AUD",
        "purchase_order_reference": "PO-1001",
    }
    with TemporaryDirectory() as directory:
        app = create_app(
            Settings(database_url=f"sqlite:///{directory}/demo.db"),
            model_provider=FakeModelProvider([analysis]),
        )
        with TestClient(app) as client:
            started = client.post("/runs", json={"financial_case": case}).json()
            run_id = started["run"]["run_id"]
            completed = client.post(
                f"/runs/{run_id}/approval",
                json={
                    "approval": {
                        "decision": "APPROVE",
                        "approver_id": "manager-1",
                        "approver_role": "Cost Centre Manager",
                        "idempotency_key": "workflow-demo-approval",
                    }
                },
            ).json()
        print(f"run_id: {run_id}")
        print(f"before approval: {started['run']['status']}")
        print(f"after approval: {completed['run']['status']}")
        print(f"simulated reference: {completed['finance_decision']['external_reference']}")
        print(f"effective submissions: {app.state.submission_metrics.execution_count}")


if __name__ == "__main__":
    main()
