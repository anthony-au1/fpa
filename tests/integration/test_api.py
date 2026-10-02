def test_health(client) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_get_run(client, case_payload: dict) -> None:
    response = client.post("/runs", json={"financial_case": case_payload})
    assert response.status_code == 201
    body = response.json()
    assert body["run"]["status"] == "WAITING_FOR_APPROVAL"
    assert body["audit_events"][0]["event_type"] == "RUN_CREATED"
    assert body["finance_decision"] is None
    assert body["pending_approval"]["status"] == "PENDING"

    run_id = body["run"]["run_id"]
    fetched = client.get(f"/runs/{run_id}")
    assert fetched.status_code == 200
    assert fetched.json()["run"]["financial_case"]["amount"] == "1100"


def test_approval_resumes_and_completes(client, case_payload: dict) -> None:
    run = client.post("/runs", json={"financial_case": case_payload}).json()["run"]
    response = client.post(
        f"/runs/{run['run_id']}/approval",
        json={
            "approval": {
                "decision": "APPROVE",
                "approver_id": "manager-1",
                "approver_role": "Cost Centre Manager",
                "idempotency_key": "approval-callback-1",
            }
        },
    )
    assert response.status_code == 200
    assert response.json()["run"]["status"] == "COMPLETE"
    assert response.json()["finance_decision"] is not None


def test_evaluations_are_explicitly_deferred(client) -> None:
    assert client.get("/evaluations").json()["evaluations"] == []
    assert client.post("/evaluations/run").status_code == 501


def test_approval_unknown_run_and_insufficient_approver(client, case_payload: dict) -> None:
    assert (
        client.post(
            "/runs/not-found/approval",
            json={
                "approval": {
                    "decision": "APPROVE",
                    "approver_id": "manager-1",
                    "approver_role": "Cost Centre Manager",
                    "idempotency_key": "missing",
                }
            },
        ).status_code
        == 404
    )
    run_id = client.post("/runs", json={"financial_case": case_payload}).json()["run"]["run_id"]
    denied = client.post(
        f"/runs/{run_id}/approval",
        json={
            "approval": {
                "decision": "APPROVE",
                "approver_id": "unknown",
                "approver_role": "Cost Centre Manager",
                "idempotency_key": "denied",
            }
        },
    )
    assert denied.status_code == 403
