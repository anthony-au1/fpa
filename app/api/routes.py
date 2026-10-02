from collections.abc import Generator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    ApprovalRequestBody,
    CreateRunRequest,
    EvaluationListResponse,
    RunResponse,
)
from app.evaluation.models import EvaluationCaseSummary, EvaluationSuiteResult
from app.persistence.repositories import RunRepository
from app.services.approvers import ApproverDenied
from app.services.workflow import ApprovalConflict, RunNotWaiting, WorkflowRunService

router = APIRouter()


def _unconfigured_session() -> Generator[Session, None, None]:
    raise RuntimeError("Database dependency was not configured")
    yield  # pragma: no cover


get_session = _unconfigured_session
SessionDependency = Annotated[Session, Depends(get_session)]


def _workflow_service(request: Request, session: Session) -> WorkflowRunService:
    return request.app.state.workflow_service_factory(session)


def _response(service: WorkflowRunService, run_id: str) -> RunResponse:
    run = service.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    approval = service.approval_context(run_id)
    return RunResponse(
        run=run,
        workflow=service.runs.load_snapshot(run_id),
        pending_approval=approval if approval and approval.status.value == "PENDING" else None,
        finance_decision=service.finance_decision(run_id),
        audit_events=RunRepository(service.deps.session).list_audit(run_id),
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    request_body: CreateRunRequest, request: Request, session: SessionDependency
) -> RunResponse:
    service = _workflow_service(request, session)
    run = await service.create_and_execute(request_body.financial_case)
    return _response(service, str(run.run_id))


@router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, request: Request, session: SessionDependency) -> RunResponse:
    return _response(_workflow_service(request, session), run_id)


@router.post("/runs/{run_id}/approval", response_model=RunResponse)
async def resolve_approval(
    run_id: str,
    request_body: ApprovalRequestBody,
    request: Request,
    session: SessionDependency,
) -> RunResponse:
    service = _workflow_service(request, session)
    try:
        await service.resolve_approval(run_id, request_body.approval)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc
    except (ApprovalConflict, RunNotWaiting) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ApproverDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _response(service, run_id)


@router.get("/evaluations", response_model=EvaluationListResponse)
def list_evaluations(request: Request) -> EvaluationListResponse:
    cases = request.app.state.evaluation_runner.cases()
    return EvaluationListResponse(
        total=len(cases),
        evaluations=[
            EvaluationCaseSummary(
                case_id=case.case_id,
                name=case.name,
                description=case.description,
            )
            for case in cases
        ],
    )


@router.post("/evaluations/run", response_model=EvaluationSuiteResult)
async def run_evaluations(request: Request) -> EvaluationSuiteResult:
    return await request.app.state.evaluation_runner.run_suite()
