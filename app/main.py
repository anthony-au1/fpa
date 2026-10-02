from collections.abc import Generator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.agent.graph import WorkflowDependencies
from app.api import routes
from app.config import Settings, get_settings
from app.evaluation.runner import EvaluationRunner
from app.llm.provider import ModelProvider, create_model_provider
from app.persistence import tables
from app.persistence.database import create_database_engine, create_session_factory
from app.rag.contracts import Retriever
from app.rag.retrieval import LocalFinanceDocumentRetriever
from app.services.approvers import FixtureApproverDirectory
from app.services.case_evidence import FixtureCaseEvidenceLoader
from app.services.workflow import WorkflowRunService
from app.tools.contracts import EvidenceTools
from app.tools.fixture_finance import FixtureFinanceTools
from app.tools.simulated_submission import (
    SimulatedFinanceDecisionSubmitter,
    SubmissionMetrics,
)


def create_app(
    settings: Settings | None = None,
    *,
    model_provider: ModelProvider | None = None,
    retriever: Retriever | None = None,
    evidence_tools: EvidenceTools | None = None,
    case_loader: FixtureCaseEvidenceLoader | None = None,
    approvers: FixtureApproverDirectory | None = None,
    submission_metrics: SubmissionMetrics | None = None,
    evaluation_runner: EvaluationRunner | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    engine = create_database_engine(active_settings.database_url)
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        tables.Base.metadata.create_all(engine)
        yield
        engine.dispose()

    application = FastAPI(
        title="Financial Processing Agent",
        version="0.1.0",
        lifespan=lifespan,
    )
    fixture_dir = active_settings.corpus_path.parent / "fixtures" / "finance"
    if not fixture_dir.exists():
        fixture_dir = Path("fixtures/finance")
    active_model = model_provider or create_model_provider(active_settings)
    active_retriever = retriever or LocalFinanceDocumentRetriever(
        active_settings.index_path,
        timeout_seconds=active_settings.rag_retrieval_timeout_seconds,
        bm25_weight=active_settings.rag_bm25_weight,
        vector_weight=active_settings.rag_vector_weight,
        metadata_weight=active_settings.rag_metadata_weight,
    )
    active_tools = evidence_tools or FixtureFinanceTools.from_directory(fixture_dir)
    active_loader = case_loader or FixtureCaseEvidenceLoader(fixture_dir / "cases.json")
    active_approvers = approvers or FixtureApproverDirectory(fixture_dir / "approvers.json")
    metrics = submission_metrics or SubmissionMetrics()
    application.state.submission_metrics = metrics
    application.state.evaluation_runner = evaluation_runner or EvaluationRunner(
        active_settings,
        fixture_dir=fixture_dir,
        cases_file=active_settings.corpus_path.parent / "fixtures" / "evaluation_cases.json"
        if (active_settings.corpus_path.parent / "fixtures" / "evaluation_cases.json").exists()
        else Path("fixtures/evaluation_cases.json"),
    )

    def workflow_service_factory(session: Session) -> WorkflowRunService:
        dependencies = WorkflowDependencies(
            session=session,
            settings=active_settings,
            retriever=active_retriever,
            evidence_tools=active_tools,
            model_provider=active_model,
            case_loader=active_loader,
            submitter=SimulatedFinanceDecisionSubmitter(session, metrics),
        )
        return WorkflowRunService(dependencies, active_approvers)

    application.state.workflow_service_factory = workflow_service_factory

    def get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    application.dependency_overrides[routes.get_session] = get_session
    application.include_router(routes.router)
    return application


app = create_app()
