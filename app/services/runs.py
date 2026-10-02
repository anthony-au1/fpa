from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.models import FinancialCase, Run
from app.persistence.repositories import RunRepository


class RunService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = RunRepository(session)

    def create(self, financial_case: FinancialCase) -> Run:
        run = self.repository.add(str(uuid4()), financial_case)
        self.session.commit()
        return run

    def get(self, run_id: str) -> Run | None:
        return self.repository.get(run_id)
