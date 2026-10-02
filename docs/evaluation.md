# Deterministic workflow evaluation

The acceptance harness exercises the existing application rather than a second finance
implementation. Each case creates a fresh temporary SQLite database and invokes the same
`WorkflowRunService`, LangGraph graph, local RAG retriever, fixture-backed finance tools, approval
directory, repositories, and simulated consequential submitter used by the HTTP application.

The suite uses an input-aware `FakeModelProvider`. It builds structured findings from chunk IDs in
the actual model input, then passes those findings through the normal `PolicyAnalysis` and citation
validation path. It does not select or change the deterministic finance outcome. No network, API key,
paid model, Docker daemon, or live finance integration is required.

## Cases

| Case | Acceptance behaviour |
| --- | --- |
| FIN-001 | Valid three-way match pauses at approval, then completes with one simulated decision. |
| FIN-002 | Exact paid duplicate exposes its stable history ID and is rejected without submission. |
| FIN-003 | ADV-001 remains evidence-only; bank/fraud controls escalate and prevent submission. |
| FIN-004 | Two bounded PO timeout attempts remain UNKNOWN and produce a safe information hold. |
| FIN-005 | An identical approval callback replay returns the completed result with one submission. |

Integration tests separately retain the conflict variants: the same callback key with a
different payload and a different key after resolution both return HTTP 409.

## Assertions and diagnostics

Every result contains named assertions with expected and actual values, stable workflow observations,
final status/outcome, duration, and a run ID for local diagnostics. Assertions inspect persisted state,
workflow snapshots, audit events, approval rows, finance-decision rows, and the simulated submitter's
execution counter. A failing assertion marks only that case failed; the suite continues. Unexpected
exceptions are reported by sanitized exception type without dumping prompts, finance fixtures, or the
database.

Citation checks require model citation IDs to have been retrieved, require current authority to remain
distinguishable, and verify ADV-001 is cited only as untrusted evidence. They deliberately avoid exact
scores, ranking positions, and generated prose.

## Commands and API

```bash
make eval
uv run python -m app.evaluation.cli --json
make eval-samples
```

`make eval` rebuilds the deterministic local index first and exits non-zero if any case fails.
`GET /evaluations` lists the five registered cases. `POST /evaluations/run` executes the deterministic
suite and returns its structured result. A completed suite returns HTTP 200 even if an assertion fails;
the result's `passed`, `failed`, and assertion fields carry evaluation status.

Generated examples under `examples/` contain stable statuses, outcomes, steps, and assertions from
real evaluation runs. Volatile UUIDs, timestamps, durations, secrets, and banking details are omitted.

## Evaluation scope

This is a small deterministic acceptance suite, not a statistical model benchmark. Evaluation
databases are intentionally ephemeral, and GET lists case definitions rather than historical suite
results. Live-model smoke tests remain separate from stable acceptance evaluation. The authoritative
project limitations are in the [design note](design-note.md#limitations-and-production-evolution).
