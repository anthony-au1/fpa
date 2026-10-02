def test_health(client) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_get_run(client, case_payload: dict) -> None:
    response = client.post("/runs", json={"financial_case": case_payload})
    assert response.status_code == 201
    body = response.json()
    assert body["run"]["status"] == "CREATED"
    assert body["audit_events"][0]["event_type"] == "RUN_CREATED"

    run_id = body["run"]["run_id"]
    fetched = client.get(f"/runs/{run_id}")
    assert fetched.status_code == 200
    assert fetched.json()["run"]["financial_case"]["amount"] == "100.10"


def test_approval_fails_closed(client, case_payload: dict) -> None:
    run = client.post("/runs", json={"financial_case": case_payload}).json()["run"]
    response = client.post(
        f"/runs/{run['run_id']}/approval",
        json={
            "approval": {
                "decision": "APPROVE",
                "approver_id": "reviewer-1",
                "approver_role": "Financial Control",
                "idempotency_key": "approval-callback-1",
            }
        },
    )
    assert response.status_code == 409


def test_evaluations_are_explicitly_deferred(client) -> None:
    assert client.get("/evaluations").json()["evaluations"] == []
    assert client.post("/evaluations/run").status_code == 501
