import pytest

from app.agent.state import AgentState, BudgetExceeded, consume_step, consume_tool_call
from app.domain.models import FinancialCase, RunStatus


def state() -> AgentState:
    return AgentState(
        run_id="run",
        financial_case=FinancialCase(
            case_id="case",
            invoice_reference="invoice",
            vendor="vendor",
            amount="1.00",
            currency="AUD",
        ),
        status=RunStatus.RUNNING,
        current_node="VALIDATE_REQUEST",
        step_count=1,
        tool_call_count=2,
        retrieved_documents=[],
        sourced_facts=[],
        calculations=[],
        policy_findings=[],
        exception_findings=[],
        unknowns=[],
    )


def test_budgets_are_enforced() -> None:
    agent_state = state()
    assert consume_step(agent_state, 2) == 2
    assert consume_tool_call(agent_state, 3) == 3
    with pytest.raises(BudgetExceeded):
        consume_step(agent_state, 1)
    with pytest.raises(BudgetExceeded):
        consume_tool_call(agent_state, 2)
