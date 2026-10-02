import argparse
import asyncio
import json
import os
from pathlib import Path

from app.config import get_settings
from app.evaluation.models import EvaluationResult, EvaluationSuiteResult
from app.evaluation.runner import EvaluationRunner

SAMPLE_FILES = {
    "FIN-001": "fin-001-success.json",
    "FIN-002": "fin-002-duplicate.json",
    "FIN-004": "fin-004-missing-evidence.json",
}


def suite_exit_code(suite: EvaluationSuiteResult) -> int:
    return 1 if suite.failed else 0


def render_summary(suite: EvaluationSuiteResult) -> str:
    lines = []
    for result in suite.results:
        status = "PASS" if result.passed else "FAIL"
        failed = [item.name for item in result.assertions if not item.passed]
        detail = result.name if not failed else f"{result.name}; failed: {', '.join(failed)}"
        lines.append(f"{result.case_id}  {status}  {detail}")
    lines.append("")
    lines.append(f"{suite.passed} passed, {suite.failed} failed")
    return "\n".join(lines)


def sample_payload(result: EvaluationResult) -> dict:
    return {
        "case_id": result.case_id,
        "name": result.name,
        "passed": result.passed,
        "steps": [step.model_dump(mode="json") for step in result.steps],
        "final_run_status": result.final_run_status,
        "final_outcome": result.final_outcome,
        "assertions": [item.model_dump(mode="json") for item in result.assertions],
    }


def write_samples(suite: EvaluationSuiteResult, destination: Path) -> None:
    if suite.failed:
        raise RuntimeError("Refusing to write samples from a failing evaluation suite")
    destination.mkdir(parents=True, exist_ok=True)
    by_id = {result.case_id: result for result in suite.results}
    for case_id, filename in SAMPLE_FILES.items():
        target = destination / filename
        temporary = target.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(sample_payload(by_id[case_id]), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, target)


async def run(arguments: argparse.Namespace) -> int:
    suite = await EvaluationRunner(get_settings()).run_suite()
    if arguments.json:
        print(json.dumps(suite.model_dump(mode="json"), indent=2, sort_keys=True))
    else:
        print(render_summary(suite))
    if arguments.samples_dir is not None:
        write_samples(suite, arguments.samples_dir)
    return suite_exit_code(suite)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic FIN-001 through FIN-005")
    parser.add_argument("--json", action="store_true", help="Print machine-readable results")
    parser.add_argument("--samples-dir", type=Path, help="Write stable sanitized sample outputs")
    return asyncio.run(run(parser.parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
