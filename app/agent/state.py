from typing import NotRequired, TypedDict

from app.domain.models import FinancialCase, RunStatus
from app.domain.workflow import WorkflowSnapshot


class AgentState(TypedDict):
    run_id: str
    financial_case: FinancialCase
    status: RunStatus
    current_node: str
    step_count: int
    tool_call_count: int
    snapshot: WorkflowSnapshot
    error: NotRequired[str | None]


class BudgetExceeded(RuntimeError):
    pass


def consume_step(state: AgentState, maximum: int) -> int:
    count = state["step_count"] + 1
    if count > maximum:
        raise BudgetExceeded(f"Graph step budget of {maximum} exceeded")
    return count


def consume_tool_call(state: AgentState, maximum: int) -> int:
    count = state["tool_call_count"] + 1
    if count > maximum:
        raise BudgetExceeded(f"Tool-call budget of {maximum} exceeded")
    return count
