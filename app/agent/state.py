from typing import NotRequired, TypedDict

from app.domain.models import (
    Calculation,
    ExceptionFinding,
    FinancialCase,
    PolicyFinding,
    Recommendation,
    RetrievedDocument,
    RunStatus,
    SourcedFact,
    Unknown,
)


class AgentState(TypedDict):
    run_id: str
    financial_case: FinancialCase
    status: RunStatus
    current_node: str
    step_count: int
    tool_call_count: int
    retrieved_documents: list[RetrievedDocument]
    sourced_facts: list[SourcedFact]
    calculations: list[Calculation]
    policy_findings: list[PolicyFinding]
    exception_findings: list[ExceptionFinding]
    unknowns: list[Unknown]
    recommendation: NotRequired[Recommendation | None]
    approval_request_id: NotRequired[str | None]
    finance_decision_id: NotRequired[str | None]
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
