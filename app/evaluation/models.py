from typing import Literal

from pydantic import Field, JsonValue

from app.domain.models import (
    ApprovalDecision,
    DomainModel,
    FinancialCase,
    RecommendationOutcome,
    RunStatus,
)
from app.tools.contracts import ToolOutcome


class EvaluationToolFailure(DomainModel):
    tool_name: Literal["get_vendor_record", "get_purchase_order", "check_invoice_history"]
    key: str
    outcome: ToolOutcome


class EvaluationCase(DomainModel):
    case_id: Literal["FIN-001", "FIN-002", "FIN-003", "FIN-004", "FIN-005"]
    name: str
    description: str
    input: FinancialCase
    tool_failures: list[EvaluationToolFailure] = Field(default_factory=list)
    approval_actions: list[ApprovalDecision] = Field(default_factory=list)
    expected_assertions: list[str] = Field(min_length=1)


class EvaluationCaseSummary(DomainModel):
    case_id: str
    name: str
    description: str


class EvaluationAssertion(DomainModel):
    name: str
    passed: bool
    expected: JsonValue
    actual: JsonValue


class EvaluationStep(DomainModel):
    action: str
    run_status: RunStatus
    outcome: RecommendationOutcome | None = None
    approval_pending: bool
    finance_decision_count: int = Field(ge=0)
    submission_execution_count: int = Field(ge=0)


class EvaluationResult(DomainModel):
    case_id: str
    name: str
    passed: bool
    assertions: list[EvaluationAssertion]
    steps: list[EvaluationStep] = Field(default_factory=list)
    final_run_status: RunStatus | None = None
    final_outcome: RecommendationOutcome | None = None
    duration_ms: int = Field(ge=0)
    run_id: str | None = None
    failure_reason: str | None = None


class EvaluationSuiteResult(DomainModel):
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    results: list[EvaluationResult]
