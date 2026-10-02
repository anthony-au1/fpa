from app.agent.graph import WorkflowDependencies, build_graph
from app.agent.state import AgentState, BudgetExceeded
from app.domain.models import ApprovalDecision, FinancialCase, Run, RunStatus
from app.domain.workflow import ApprovalContext, WorkflowStage
from app.persistence.repositories import (
    ApprovalRepository,
    FinanceDecisionRepository,
    RunRepository,
)
from app.services.approvers import FixtureApproverDirectory


class ApprovalConflict(RuntimeError):
    pass


class RunNotWaiting(RuntimeError):
    pass


class WorkflowRunService:
    def __init__(
        self, dependencies: WorkflowDependencies, approvers: FixtureApproverDirectory
    ) -> None:
        self.deps = dependencies
        self.approvers = approvers
        self.runs = RunRepository(dependencies.session)

    async def create_and_execute(self, case: FinancialCase) -> Run:
        from uuid import uuid4

        run = self.runs.add(str(uuid4()), case)
        self.deps.session.commit()
        return await self.execute(str(run.run_id))

    async def execute(self, run_id: str) -> Run:
        run = self.runs.get(run_id)
        if run is None:
            raise KeyError(run_id)
        snapshot = self.runs.load_snapshot(run_id)
        state: AgentState = {
            "run_id": run_id,
            "financial_case": run.financial_case,
            "status": run.status,
            "current_node": run.current_node or "START",
            "step_count": run.step_count,
            "tool_call_count": run.tool_call_count,
            "snapshot": snapshot,
            "error": run.error,
        }
        try:
            await build_graph(self.deps).ainvoke(state)
        except Exception as exc:
            self.deps.session.rollback()
            current = self.runs.get(run_id)
            if current is None:
                raise
            if current.status not in {RunStatus.COMPLETE, RunStatus.FAILED}:
                failure_snapshot = self.runs.load_snapshot(run_id).model_copy(
                    update={"next_stage": WorkflowStage.FAILED}
                )
                code = self._failure_code(exc)
                self.runs.append_audit(
                    run_id,
                    "RUN_FAILED",
                    "workflow",
                    {"reason": code, "node": current.current_node},
                )
                self.runs.save_snapshot(
                    run_id,
                    failure_snapshot,
                    status=RunStatus.FAILED,
                    current_node="FAILED",
                    step_count=current.step_count,
                    tool_call_count=current.tool_call_count,
                    recommendation=failure_snapshot.recommendation,
                    error=code,
                )
                self.deps.session.commit()
        result = self.runs.get(run_id)
        if result is None:  # pragma: no cover
            raise KeyError(run_id)
        return result

    async def resolve_approval(self, run_id: str, decision: ApprovalDecision) -> Run:
        run = self.runs.get(run_id)
        if run is None:
            raise KeyError(run_id)
        approvals = ApprovalRepository(self.deps.session)
        row = approvals.get_for_run(run_id)
        if row is None:
            raise RunNotWaiting("Run has no approval request")
        existing = approvals.decision(row)
        if existing is not None:
            if row.callback_idempotency_key != decision.idempotency_key:
                raise ApprovalConflict(
                    "Approval request was already resolved by a different callback"
                )
            if not self._same_callback_payload(existing, decision):
                raise ApprovalConflict("Approval callback key was reused with a different payload")
            if run.status is RunStatus.RUNNING:
                return await self.execute(run_id)
            return run
        if run.status is not RunStatus.WAITING_FOR_APPROVAL:
            raise RunNotWaiting("Run is not waiting for approval")
        context = approvals.to_context(row)
        self.approvers.validate(decision, context)
        approvals.resolve(row, decision)
        snapshot = self.runs.load_snapshot(run_id).model_copy(
            update={
                "approval_decision": decision,
                "next_stage": WorkflowStage.RESOLVE_APPROVAL,
            }
        )
        self.runs.append_audit(
            run_id,
            "APPROVAL_RESOLVED",
            "human",
            {"decision": decision.decision},
            actor_id=decision.approver_id,
        )
        self.runs.save_snapshot(
            run_id,
            snapshot,
            status=RunStatus.RUNNING,
            current_node="APPROVAL_RESOLVED",
            step_count=run.step_count,
            tool_call_count=run.tool_call_count,
            recommendation=snapshot.recommendation,
        )
        self.deps.session.commit()
        return await self.execute(run_id)

    def approval_context(self, run_id: str) -> ApprovalContext | None:
        row = ApprovalRepository(self.deps.session).get_for_run(run_id)
        return None if row is None else ApprovalRepository.to_context(row)

    def finance_decision(self, run_id: str):
        return FinanceDecisionRepository(self.deps.session).get_for_run(run_id)

    @staticmethod
    def _same_callback_payload(existing: ApprovalDecision, incoming: ApprovalDecision) -> bool:
        return (
            existing.decision == incoming.decision
            and existing.approver_id == incoming.approver_id
            and existing.approver_role == incoming.approver_role
            and existing.comment == incoming.comment
        )

    @staticmethod
    def _failure_code(exc: Exception) -> str:
        if isinstance(exc, BudgetExceeded):
            return "EXECUTION_BUDGET_EXCEEDED"
        message = str(exc)
        if message == "MODEL_ANALYSIS_FAILED":
            return message
        if "case" in message.casefold() or "evidence" in message.casefold():
            return "CASE_EVIDENCE_INVALID"
        return "WORKFLOW_EXECUTION_FAILED"
