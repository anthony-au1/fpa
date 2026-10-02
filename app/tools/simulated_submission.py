import hashlib
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.models import ApprovalStatus, FinanceDecision, RecommendationOutcome
from app.persistence.repositories import ApprovalRepository, FinanceDecisionRepository
from app.tools.contracts import ConsequentialToolDenied, FinanceSubmissionCommand


class SimulatedFinanceDecisionSubmitter:
    """Database-backed simulation. It has no external finance-system capability."""

    def __init__(self, session: Session, metrics: "SubmissionMetrics | None" = None) -> None:
        self.session = session
        self.metrics = metrics or SubmissionMetrics()

    @property
    def execution_count(self) -> int:
        return self.metrics.execution_count

    async def submit(self, command: FinanceSubmissionCommand) -> FinanceDecision:
        existing = FinanceDecisionRepository(self.session).get_for_run(command.run_id)
        if existing is not None:
            return existing
        approval = ApprovalRepository(self.session).get_for_run(command.run_id)
        if approval is None or approval.status != ApprovalStatus.APPROVED.value:
            raise ConsequentialToolDenied("Persisted approved human decision is required")
        context = ApprovalRepository.to_context(approval)
        if context.recommendation.outcome is not RecommendationOutcome.APPROVE_FOR_POSTING:
            raise ConsequentialToolDenied("Recommendation is not eligible for submission")
        if command.recommendation_outcome != RecommendationOutcome.APPROVE_FOR_POSTING.value:
            raise ConsequentialToolDenied("Submission command conflicts with recommendation")
        expected_key = finance_decision_key(command.run_id, command.recommendation_outcome)
        if command.idempotency_key != expected_key:
            raise ConsequentialToolDenied("Invalid finance-decision idempotency key")
        external_reference = "SIM-" + hashlib.sha256(expected_key.encode()).hexdigest()[:16]
        decision = FinanceDecisionRepository(self.session).create(
            run_id=command.run_id,
            outcome=command.recommendation_outcome,
            idempotency_key=command.idempotency_key,
            external_reference=external_reference,
        )
        self.metrics.execution_count += 1
        return decision


def finance_decision_key(run_id: str, outcome: str) -> str:
    canonical = f"finance-decision:v1|{run_id}|{outcome}"
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class SubmissionMetrics:
    execution_count: int = 0
