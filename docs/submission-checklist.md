# Submission checklist

Verification date: 2026-10-02. Checkboxes are marked only after the final command or inspection
completed successfully.

- [x] Clean checkout/export setup verified
- [x] Python 3.12 requirement documented
- [x] Dependencies install from committed `uv.lock`
- [x] Supplied corpus remains unchanged and ingests successfully
- [x] Tests pass
- [x] RAG evaluation passes
- [x] FIN-001–FIN-005 evaluation passes
- [x] Docker Compose configuration validates
- [x] Docker image builds
- [x] Sanitized examples regenerated from the evaluator
- [x] Secret and credential scan completed
- [x] Sensitive logging/audit minimization reviewed
- [x] No runtime database, index, cache, editor metadata, or archive committed
- [x] `.env.example` is present and contains placeholders only
- [x] README commands and API payloads verified
- [x] Design note present
- [x] Architecture and workflow diagrams present
- [x] Component manifest present
- [x] Requirements traceability matrix present
- [x] AI-tool and approximate-time disclosure present
- [x] Authoritative known-limitations section documented
- [x] Policy IDs/versions and historical-only semantics rechecked
