from decimal import Decimal
from enum import StrEnum

from pydantic import Field

from app.domain.finance import DeterministicControlResult, InvoiceEvidence
from app.domain.models import (
    ApprovalDecision,
    ApprovalStatus,
    Citation,
    DomainModel,
    Money,
    Recommendation,
    RetrievedDocument,
)
from app.tools.contracts import (
    InvoiceHistoryToolResult,
    PurchaseOrderToolResult,
    VendorToolResult,
)


class WorkflowStage(StrEnum):
    VALIDATE_REQUEST = "VALIDATE_REQUEST"
    RETRIEVE_POLICY = "RETRIEVE_POLICY"
    GATHER_EVIDENCE = "GATHER_EVIDENCE"
    RECONCILE = "RECONCILE"
    POLICY_ANALYSIS = "POLICY_ANALYSIS"
    BUILD_RECOMMENDATION = "BUILD_RECOMMENDATION"
    CREATE_APPROVAL_REQUEST = "CREATE_APPROVAL_REQUEST"
    RESOLVE_APPROVAL = "RESOLVE_APPROVAL"
    SUBMIT_FINANCE_DECISION = "SUBMIT_FINANCE_DECISION"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class EvidenceBundle(DomainModel):
    vendor: VendorToolResult
    purchase_order: PurchaseOrderToolResult | None = None
    invoice_history: InvoiceHistoryToolResult


class AnalysisSourcedFinding(DomainModel):
    finding_id: str
    statement: str
    citation_chunk_ids: list[str] = Field(min_length=1)


class AnalysisPolicyFinding(DomainModel):
    finding_id: str
    rule: str
    explanation: str
    citation_chunk_ids: list[str] = Field(min_length=1)


class AnalysisInference(DomainModel):
    inference_id: str
    statement: str
    basis_ids: list[str] = Field(default_factory=list)


class AnalysisUnknown(DomainModel):
    unknown_id: str
    field: str
    reason: str


class PolicyAnalysis(DomainModel):
    sourced_findings: list[AnalysisSourcedFinding]
    policy_findings: list[AnalysisPolicyFinding]
    inferences: list[AnalysisInference]
    unknowns: list[AnalysisUnknown]
    explanation: str
    confidence: Decimal = Field(ge=0, le=1)


class ApprovalContext(DomainModel):
    approval_request_id: str
    run_id: str
    status: ApprovalStatus
    case_id: str
    vendor: str
    amount: Money
    currency: str
    recommendation: Recommendation
    citations: list[Citation] = Field(default_factory=list)
    exception_ids: list[str] = Field(default_factory=list)
    unknown_ids: list[str] = Field(default_factory=list)
    required_approval_roles: list[str] = Field(default_factory=list)


class WorkflowSnapshot(DomainModel):
    invoice_evidence: InvoiceEvidence | None = None
    retrieved_documents: list[RetrievedDocument] = Field(default_factory=list)
    evidence: EvidenceBundle | None = None
    control_result: DeterministicControlResult | None = None
    policy_analysis: PolicyAnalysis | None = None
    recommendation: Recommendation | None = None
    approval_decision: ApprovalDecision | None = None
    next_stage: WorkflowStage = WorkflowStage.VALIDATE_REQUEST


class ApproverRecord(DomainModel):
    approver_id: str
    display_name: str
    roles: list[str]
    maximum_approval_aud: Money | None = None
    active: bool = True
