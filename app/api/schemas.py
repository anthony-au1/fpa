from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import ApprovalDecision, AuditEvent, FinanceDecision, FinancialCase, Run
from app.domain.workflow import ApprovalContext, WorkflowSnapshot
from app.evaluation.models import EvaluationCaseSummary


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


class EvaluationListResponse(ApiModel):
    total: int
    evaluations: list[EvaluationCaseSummary]


class Problem(ApiModel):
    detail: str
