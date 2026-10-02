from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.models import AuditEvent, FinancialCase, Run, RunStatus, utc_now
from app.observability.redaction import redact_sensitive
from app.persistence.tables import AuditEventRow, RunRow


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

    def append_audit(
        self, run_id: str, event_type: str, actor_type: str, payload: dict
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
