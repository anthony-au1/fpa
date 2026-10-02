import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.evaluation.cli import SAMPLE_FILES, suite_exit_code, write_samples
from app.evaluation.models import EvaluationAssertion, EvaluationSuiteResult
from app.evaluation.runner import CASE_ASSERTIONS, EvaluationRunner, load_evaluation_cases
from app.main import create_app
from app.rag.ingestion import build_index


@pytest.fixture(scope="module")
def evaluation_settings(tmp_path_factory: pytest.TempPathFactory) -> Settings:
    index_path = tmp_path_factory.mktemp("workflow-evaluation-index")
    build_index(
        Path("finance_rag_corpus"),
        index_path,
        embedding_provider="local_tfidf",
        maximum_chunk_chars=1800,
    )
    return Settings(index_path=index_path, llm_provider="disabled")


@pytest.fixture(scope="module")
def evaluation_suite(evaluation_settings: Settings) -> EvaluationSuiteResult:
    return asyncio.run(EvaluationRunner(evaluation_settings).run_suite())


def assertion(result, name: str) -> EvaluationAssertion:
    return next(item for item in result.assertions if item.name == name)


def test_all_five_cases_are_registered() -> None:
    cases = load_evaluation_cases(Path("fixtures/evaluation_cases.json"))
    assert [case.case_id for case in cases] == [
        "FIN-001",
        "FIN-002",
        "FIN-003",
        "FIN-004",
        "FIN-005",
    ]


def test_deterministic_suite_passes_all_five(evaluation_suite: EvaluationSuiteResult) -> None:
    assert evaluation_suite.total == 5
    assert evaluation_suite.passed == 5
    assert evaluation_suite.failed == 0
    assert all(result.passed for result in evaluation_suite.results)


def test_cases_are_isolated(evaluation_suite: EvaluationSuiteResult) -> None:
    assert len({result.run_id for result in evaluation_suite.results}) == 5
    for case_id in ("FIN-001", "FIN-005"):
        result = next(item for item in evaluation_suite.results if item.case_id == case_id)
        assert assertion(result, "submission_exactly_once").actual == 1


def test_failed_assertion_is_reported_without_aborting_suite(
    evaluation_settings: Settings,
) -> None:
    def deliberate_failure(_record) -> list[EvaluationAssertion]:
        return [
            EvaluationAssertion(
                name="terminal_status",
                passed=False,
                expected="COMPLETE",
                actual="FAILED",
            )
        ]

    evaluators = {**CASE_ASSERTIONS, "FIN-002": deliberate_failure}
    suite = asyncio.run(
        EvaluationRunner(evaluation_settings, assertion_evaluators=evaluators).run_suite()
    )
    failed = next(result for result in suite.results if result.case_id == "FIN-002")
    assert not failed.passed
    assert any(not item.passed for item in failed.assertions)
    assert suite.total == 5
    assert suite.passed == 4


def test_evaluation_api_uses_no_live_model_credentials(
    tmp_path: Path, evaluation_settings: Settings
) -> None:
    settings = evaluation_settings.model_copy(
        update={"database_url": f"sqlite:///{tmp_path / 'api.db'}", "llm_provider": "disabled"}
    )
    app = create_app(settings)
    with TestClient(app) as client:
        listed = client.get("/evaluations")
        executed = client.post("/evaluations/run")
    assert listed.status_code == 200
    assert listed.json()["total"] == 5
    assert executed.status_code == 200
    assert executed.json()["passed"] == 5
    assert executed.json()["failed"] == 0


def test_cli_exit_code_reflects_suite_result(evaluation_suite: EvaluationSuiteResult) -> None:
    assert suite_exit_code(evaluation_suite) == 0
    failing = evaluation_suite.model_copy(update={"passed": 4, "failed": 1})
    assert suite_exit_code(failing) == 1


def test_sample_generation_is_stable_and_sanitized(
    tmp_path: Path, evaluation_suite: EvaluationSuiteResult
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_samples(evaluation_suite, first)
    write_samples(evaluation_suite, second)
    for filename in SAMPLE_FILES.values():
        first_content = (first / filename).read_text()
        assert first_content == (second / filename).read_text()
        assert "run_id" not in first_content
        assert "duration_ms" not in first_content
        assert "bank_account" not in first_content
