from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.models import (
    ApprovalDecision,
    ApprovalStatus,
    AuditEvent,
    FinanceDecision,
    FinancialCase,
    Recommendation,
    Run,
    RunStatus,
    utc_now,
)
from app.domain.transitions import validate_transition
from app.domain.workflow import ApprovalContext, WorkflowSnapshot
from app.observability.redaction import redact_sensitive
from app.persistence.tables import ApprovalRequestRow, AuditEventRow, FinanceDecisionRow, RunRow


class RunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, run_id: str, case: FinancialCase) -> Run:
        now = utc_now()
        row = RunRow(
            id=run_id,
            case_id=case.case_id,
            case_payload=case.model_dump(mode="json"),
            state_payload={},
            status=RunStatus.CREATED,
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        self.session.flush()
        self.append_audit(row.id, "RUN_CREATED", "api", {"case_id": case.case_id})
        return self._to_domain(row)

    def get(self, run_id: str) -> Run | None:
        row = self.session.get(RunRow, run_id)
        return None if row is None else self._to_domain(row)

    def get_row(self, run_id: str) -> RunRow | None:
        return self.session.get(RunRow, run_id)

    def load_snapshot(self, run_id: str) -> WorkflowSnapshot:
        row = self.session.get(RunRow, run_id)
        if row is None:
            raise KeyError(run_id)
        return WorkflowSnapshot.model_validate(row.state_payload or {})

    def save_snapshot(
        self,
        run_id: str,
        snapshot: WorkflowSnapshot,
        *,
        status: RunStatus,
        current_node: str,
        step_count: int,
        tool_call_count: int,
        recommendation: Recommendation | None = None,
        error: str | None = None,
    ) -> Run:
        row = self.session.get(RunRow, run_id)
        if row is None:
            raise KeyError(run_id)
        current = RunStatus(row.status)
        if current != status:
            validate_transition(current, status)
        row.state_payload = snapshot.model_dump(mode="json")
        row.status = status.value
        row.current_node = current_node
        row.step_count = step_count
        row.tool_call_count = tool_call_count
        row.recommendation_payload = (
            recommendation.model_dump(mode="json") if recommendation else None
        )
        row.error = error
        row.version += 1
        row.updated_at = utc_now()
        self.session.flush()
        return self._to_domain(row)

    def append_audit(
        self,
        run_id: str,
        event_type: str,
        actor_type: str,
        payload: dict,
        actor_id: str | None = None,
    ) -> AuditEvent:
        sequence = self.session.scalar(
            select(func.coalesce(func.max(AuditEventRow.sequence), 0) + 1).where(
                AuditEventRow.run_id == run_id
            )
        )
        event = AuditEvent(
            run_id=run_id,
            sequence=sequence or 1,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            payload=redact_sensitive(payload),
        )
        self.session.add(
            AuditEventRow(
                id=str(event.event_id),
                run_id=run_id,
                sequence=event.sequence,
                event_type=event.event_type,
                actor_type=event.actor_type,
                actor_id=event.actor_id,
                payload=event.payload,
                created_at=event.created_at,
            )
        )
        return event

    def list_audit(self, run_id: str) -> list[AuditEvent]:
        rows = self.session.scalars(
            select(AuditEventRow)
            .where(AuditEventRow.run_id == run_id)
            .order_by(AuditEventRow.sequence)
        )
        return [
            AuditEvent(
                event_id=row.id,
                run_id=row.run_id,
                sequence=row.sequence,
                event_type=row.event_type,
                actor_type=row.actor_type,
                actor_id=row.actor_id,
                payload=row.payload,
                created_at=row.created_at,
            )
            for row in rows
        ]

    @staticmethod
    def _to_domain(row: RunRow) -> Run:
        return Run(
            run_id=row.id,
            financial_case=FinancialCase.model_validate(row.case_payload),
            status=row.status,
            current_node=row.current_node,
            step_count=row.step_count,
            tool_call_count=row.tool_call_count,
            recommendation=row.recommendation_payload,
            error=row.error,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class ApprovalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_for_run(self, run_id: str) -> ApprovalRequestRow | None:
        return self.session.scalar(
            select(ApprovalRequestRow).where(ApprovalRequestRow.run_id == run_id)
        )

    def create_or_get(self, context: ApprovalContext, idempotency_key: str) -> ApprovalContext:
        existing = self.get_for_run(context.run_id)
        if existing is not None:
            return self.to_context(existing)
        row = ApprovalRequestRow(
            id=context.approval_request_id,
            run_id=context.run_id,
            status=ApprovalStatus.PENDING.value,
            idempotency_key=idempotency_key,
            recommendation_payload=context.model_dump(mode="json"),
            requested_at=utc_now(),
        )
        self.session.add(row)
        self.session.flush()
        return context

    def resolve(self, row: ApprovalRequestRow, decision: ApprovalDecision) -> None:
        row.status = (
            ApprovalStatus.APPROVED.value
            if decision.decision.value == "APPROVE"
            else ApprovalStatus.REJECTED.value
        )
        row.decision_payload = decision.model_dump(mode="json")
        row.callback_idempotency_key = decision.idempotency_key
        row.decided_at = decision.decided_at
        self.session.flush()

    @staticmethod
    def to_context(row: ApprovalRequestRow) -> ApprovalContext:
        payload = dict(row.recommendation_payload)
        payload["status"] = row.status
        return ApprovalContext.model_validate(payload)

    @staticmethod
    def decision(row: ApprovalRequestRow) -> ApprovalDecision | None:
        return (
            None
            if row.decision_payload is None
            else ApprovalDecision.model_validate(row.decision_payload)
        )


class FinanceDecisionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_for_run(self, run_id: str) -> FinanceDecision | None:
        row = self.session.scalar(
            select(FinanceDecisionRow).where(FinanceDecisionRow.run_id == run_id)
        )
        return None if row is None else self.to_domain(row)

    def create(
        self, *, run_id: str, outcome: str, idempotency_key: str, external_reference: str
    ) -> FinanceDecision:
        existing = self.get_for_run(run_id)
        if existing is not None:
            return existing
        row = FinanceDecisionRow(
            id=str(uuid4()),
            run_id=run_id,
            outcome=outcome,
            idempotency_key=idempotency_key,
            external_reference=external_reference,
            created_at=utc_now(),
        )
        self.session.add(row)
        self.session.flush()
        return self.to_domain(row)

    @staticmethod
    def to_domain(row: FinanceDecisionRow) -> FinanceDecision:
        return FinanceDecision(
            finance_decision_id=row.id,
            run_id=row.run_id,
            recommendation_outcome=row.outcome,
            idempotency_key=row.idempotency_key,
            external_reference=row.external_reference,
            created_at=row.created_at,
        )
