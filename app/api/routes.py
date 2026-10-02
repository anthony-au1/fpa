from collections.abc import Generator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    ApprovalRequestBody,
    CreateRunRequest,
    EvaluationListResponse,
    Problem,
    RunResponse,
)
from app.domain.models import RunStatus
from app.persistence.repositories import RunRepository
from app.services.runs import RunService

router = APIRouter()


def _unconfigured_session() -> Generator[Session, None, None]:
    raise RuntimeError("Database dependency was not configured")
    yield  # pragma: no cover


get_session = _unconfigured_session
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def create_run(request: CreateRunRequest, session: SessionDependency) -> RunResponse:
    run = RunService(session).create(request.financial_case)
    audit = RunRepository(session).list_audit(str(run.run_id))
    return RunResponse(run=run, audit_events=audit)


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, session: SessionDependency) -> RunResponse:
    service = RunService(session)
    run = service.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse(run=run, audit_events=RunRepository(session).list_audit(run_id))


@router.post("/runs/{run_id}/approval", response_model=Problem)
def resolve_approval(
    run_id: str,
    _request: ApprovalRequestBody,
    session: SessionDependency,
) -> Problem:
    run = RunService(session).get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status != RunStatus.WAITING_FOR_APPROVAL:
        raise HTTPException(status_code=409, detail="Run is not waiting for approval")
    raise HTTPException(
        status_code=501,
        detail="Approval resume execution is intentionally deferred from the foundation task",
    )


@router.get("/evaluations", response_model=EvaluationListResponse)
def list_evaluations() -> EvaluationListResponse:
    return EvaluationListResponse()


@router.post("/evaluations/run", response_model=Problem, status_code=501)
def run_evaluations() -> Problem:
    raise HTTPException(
        status_code=501,
        detail="Evaluation execution is intentionally deferred from the foundation task",
    )
