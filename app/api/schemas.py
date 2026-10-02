from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import ApprovalDecision, AuditEvent, FinanceDecision, FinancialCase, Run
from app.domain.workflow import ApprovalContext, WorkflowSnapshot


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateRunRequest(ApiModel):
    financial_case: FinancialCase


class RunResponse(ApiModel):
    run: Run
    workflow: WorkflowSnapshot
    pending_approval: ApprovalContext | None = None
    finance_decision: FinanceDecision | None = None
    audit_events: list[AuditEvent] = Field(default_factory=list)


class ApprovalRequestBody(ApiModel):
    approval: ApprovalDecision


class EvaluationSummary(ApiModel):
    evaluation_id: str
    status: Literal["NOT_IMPLEMENTED"] = "NOT_IMPLEMENTED"


class EvaluationListResponse(ApiModel):
    evaluations: list[EvaluationSummary] = Field(default_factory=list)
    detail: str = "Evaluation fixtures and execution are deferred from the foundation task."


class Problem(ApiModel):
    detail: str
