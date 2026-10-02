# Evaluation tests

The workflow evaluator runs FIN-001 through FIN-005 through the real application services with a
fresh SQLite database per case, the actual local RAG index, deterministic fixture tools, and an
input-aware `FakeModelProvider`. These tests validate the evaluator and externally meaningful
acceptance behaviour; lower-level finance and workflow rules remain covered by their focused suites.
