# LangGraph, MongoDB and FastAPI fixes

Verified on 30 October 2026 against baseline `31de859` on
`feat/prepayment-validator`. These changes follow the approved core review.
The [architecture report](AGENT_REFACTOR_REPORT.md) retains the worked agent
request, interaction diagram and repository trees; the directory layout is
unchanged by this follow-up.

## Changes

| Area | Files and functions | Change and reason |
|---|---|---|
| LangGraph | `app/agents/orchestrator.py`: `_validation_response`, `validate`, `revalidate` | Extract the identical validation-to-response mapping. Proposal hashing, approval checks, node names, edges and state fields remain unchanged. |
| Checkpoints | `app/database/agent_runs.py`: `_CHECKPOINT_MODELS`, `MongoRunStore.__init__` | Declare the same ordered 16 model classes once. Serializer module/class identities and JSON/MessagePack permissions remain unchanged. |
| FastAPI | `app/api/answer.py`: `_ANSWER_ERRORS`, `answer`, `evaluated_answer` | Share the same seven exception types. Each endpoint retains its own service, log event, validation and safe HTTP 503 response. |
| Ingestion scope | `app/chains/ingestion.py`: `parse`, `compare` | Reject requests outside the configured corpus and reject colliding chunks or existing exact-document parents with conflicting or missing identity/scope metadata before embedding or writing. |
| Stale cleanup | `app/database/mongo.py`: `delete_stale_chunks`; `app/services/ingestion.py`: `ingest` | Require keyword-only `settings` and filter obsolete chunks by institution, jurisdiction and confidentiality as well as document ID. Pass the chain's configuration through the service. |
| Regression coverage and guides | `tests/test_answer.py`, `tests/test_ingestion.py`, README, C4 inventories, two code tours | Add 35 cases, preserve previous assertions and update affected signatures, behavior descriptions and tour anchors. |

The first three changes are structural. The ingestion guard is an intentional
safety correction: previously stale cleanup could delete another corpus's chunks
sharing a document ID, and colliding chunk/parent keys could overwrite or remove
foreign records. Stored IDs, collection names, public model paths and graph
checkpoint keys are preserved. No migration runs.

## Ingestion operating guide

1. Use the authoritative document register and the existing ingestion command:
   `uv run --locked --no-sync --env-file .env python -m app.services.ingestion nexa_synthetic_data/document_register.json`.
   Register requests receive institution, jurisdiction and confidentiality from
   settings. Programmatically constructed `IngestRequest` values must match those
   same three settings.
2. Run one ingestion job at a time. Parsing and enrichment retain their existing
   LCEL stage names. Before embeddings, `compare` reads current child IDs and
   all exact-document parent keys, including obsolete parents, through the
   existing `VectorStore` and `BaseStore` interfaces.
3. Existing identities must have matching `doc_id`, `institution`, `jurisdiction`
   and `confidentiality_level`. A conflict or missing scope raises
   `ValueError("Stored document identity has conflicting or missing corpus scope")`
   before that document's embedding/upsert or parent cleanup. A request/configuration
   conflict raises `ValueError("Ingestion scope must match the configured corpus")`
   before parsing. Earlier successful documents in a batch remain committed.
4. On a conflict, back up the affected collections and verify record provenance.
   Correct metadata only from verified source material. Assign a distinct document
   ID or use separate corpus collections when two corpora need different documents
   with the same legacy identity. Re-run ingestion after resolving the conflict.
5. Successful ingestion preserves checksum-based reuse and writes changed children
   before parents. Stale cleanup then removes only matching-corpus chunks omitted
   from the new result. Foreign and unscoped chunks are preserved.

Direct callers must now supply the explicit corpus scope:

```python
removed = delete_stale_chunks(collection, doc_id, keep_ids, settings=settings)
```

Chunk/parent writes still span collections without a transaction or job lock.
The pre-write checks protect sequential ingestion; they do not establish isolation
against concurrent writers or provide rollback after partial write failures.
Support for concurrent multi-corpus writes needs a separate identity/transaction
design and migration plan.

## Verification

| Check | Before | After |
|---|---|---|
| Root pytest suite | 580 passed | 615 passed |
| Application line coverage | 85.65% | 86.15%; unchanged floor 84.13% |
| Changed executable application lines | — | 22 covered, 0 missing, 100% |
| Ruff lint / format | Pass; 116 files formatted | Pass; 116 files formatted |
| mypy | Pass; 106 files | Pass; 106 files |
| Floor guard | Prior release passed | 0 violations against `31de859` |
| Separate synthetic banking/OpenAPI suite | Prior release: 22 passed | 22 passed |
| Semgrep / security gate | Six previously recorded findings | 0 new ERROR findings, 0 scan errors; six existing findings remain |
| Graph/checkpoint compatibility | Pre-change source retained for comparison | Same 16 class objects in the same order; graph calls and state types match; a pre-change checkpoint restores through the updated store |
| HTTP/startup compatibility | Pre-change router retained for comparison | Entire RAG OpenAPI schema unchanged; both real API lifespans start and return `/health` HTTP 200 |

The full command was `make check-full BASE_REF=31de859`. The banking command was
`uv run --locked --no-sync pytest nexa_synthetic_data/api/mock_server/test_mock_api.py -q`.
The 35 additional cases cover both answer routes' seven handled failure types,
request-scope conflicts, child/current-parent/obsolete-parent conflicts across
all identity fields, missing scope, and successful service cleanup. Two cases
exercise the actual LangChain MongoDB adapters against isolated mock collections.
Existing workflow tests continue exercising prepare, approve/reject, revalidation,
uncertain-submission retry and the Streamlit owner/reviewer flow.

[Machine-readable verification](core-fixes-verification-20261030.json) includes
the commands, compatibility results and hashes of tested source files. Local logs
and the compatibility smoke script are in `/private/tmp/nexa-core-fixes-20261030`;
these temporary files are supplementary evidence, not runtime dependencies.

## Release limits

- Live Atlas, provider scoring, Datadog ingestion and production load were not
  checked. MongoDB persistence checks here use isolated mock collections with
  the actual MongoDB checkpoint serializer and LangChain adapters. Health confirms
  application startup/liveness, not external dependency readiness.
- The six pre-existing security findings remain recorded; the passing gate only
  establishes no new ERROR fingerprints and no scanner errors.
- Continue the existing service-request process: prepare as owner, save the run
  ID, switch to a different authorized reviewer, load that same run and decide it.
  See the [service-request guide](SERVICE_REQUESTS_GUIDE.md) for customer/type scope.
- Constraints, secrets/env files, dependency declarations, lockfiles and CI were
  unchanged. No deployment or push was performed.
- Each logical change is committed separately with Pankaj as author and committer,
  with no co-author trailers. Unrelated untracked work is preserved.
