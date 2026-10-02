from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.persistence.database import Base, create_database_engine, create_session_factory
from app.persistence.tables import ApprovalRequestRow, FinanceDecisionRow, RunRow


def test_one_finance_decision_per_run() -> None:
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    run_id = str(uuid4())
    with factory() as session:
        session.add(
            RunRow(
                id=run_id,
                case_id="case",
                case_payload={},
                state_payload={},
                status="CREATED",
            )
        )
        session.flush()
        session.add(
            FinanceDecisionRow(
                id=str(uuid4()),
                run_id=run_id,
                outcome="APPROVE_FOR_POSTING",
                idempotency_key="decision-1",
            )
        )
        session.commit()
        session.add(
            FinanceDecisionRow(
                id=str(uuid4()),
                run_id=run_id,
                outcome="APPROVE_FOR_POSTING",
                idempotency_key="decision-2",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_duplicate_approval_callback_key_is_rejected() -> None:
    engine = create_database_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    run_id = str(uuid4())
    with factory() as session:
        session.add(
            RunRow(
                id=run_id,
                case_id="case",
                case_payload={},
                state_payload={},
                status="WAITING_FOR_APPROVAL",
            )
        )
        session.flush()
        first = ApprovalRequestRow(
            id=str(uuid4()),
            run_id=run_id,
            status="APPROVED",
            idempotency_key="request-1",
            callback_idempotency_key="callback-1",
            recommendation_payload={},
        )
        session.add(first)
        session.commit()
        session.add(
            ApprovalRequestRow(
                id=str(uuid4()),
                run_id=run_id,
                status="REJECTED",
                idempotency_key="request-2",
                callback_idempotency_key="callback-1",
                recommendation_payload={},
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
