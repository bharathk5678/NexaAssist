# NexaAssist repository reference

Generated from the current working tree on 2026-10-24 (Asia/Kolkata). This is a component-level view of the implementation, including existing modified and untracked files. It is not a live deployment inventory.

[Open interactive architecture](nexaassist.html) · [RAG OpenAPI](rag-openapi.json) · [Agent OpenAPI](agent-openapi.json) · [Source snapshot and changed paths](source-state.json)

## Source identity

Original repository HEAD: `2bc16cc634cca62e6153db65833235420ae66305`. Evidence is pinned to local documentation snapshot `f60cdc91dff45b8aca880f19db71e2834b8ecc58`. This snapshot is stored in `source-snapshot/`; its commit is not part of the original project history or available on the remote. No `.env`, credentials, customer datasets, binaries, vectors or runtime evaluation reports were copied.

## Runtime boundaries

| Component | Entry point / configuration | Responsibility |
|---|---|---|
| RAG API | `app.main:app`; Docker exposes 8000 | Retrieval, grounded answer, live quality evaluation, feedback and operations |
| Agent Service | `app.agent_main:app`; example local port 8001 | Intent classification, scope gate, one HTTP retrieval and grounded answer |
| Streamlit | `app/streamlit_app.py`; `UISettings.api_base_url` | Calls RAG endpoints; keeps chat state local to the UI session |
| Ingestion | `python -m app.services.ingestion <register>` | Authoritative document write path and explicit retirement |
| Offline evaluation | `python -m app.evaluation.run` | Golden-case answer capture, RAGAS, structured judge and report |
| MongoDB Atlas | URI/database/collections from Settings | Embedded children, unembedded parents and feedback records |
| OpenAI integrations | `get_chat_model`, `get_embeddings` | Configured chat/structured output and embedding calls |
| Optional reranker | `RERANK_ENABLED`, `RERANK_API`, `RERANK_BASE_URL` | Ollama or OpenAI-compatible pair scoring; no server is launched here |
| Datadog | `ddtrace-run`, `DD_*`, `app/compose.datadog.yaml` | Optional APM/LLM telemetry and score/feedback joins; compose starts only the Agent |
| Banking mock | `nexa_synthetic_data/api/mock_server/server.py` | Standalone synthetic reads/writes; disconnected from Agent Service |

## Registered application APIs

The tables include all explicitly registered application operations. Both FastAPI apps also expose their default `/docs`, `/redoc`, `/openapi.json` and `/docs/oauth2-redirect` routes. Authentication below describes route dependencies visible in this code; external proxy or deployment authentication was not inspected.

### RAG application

| Method and path | Input | Output | Authentication | Outcomes / conditions |
|---|---|---|---|---|
| `GET /health` | None | {status: ok} | None declared | 200; no dependency health probe |
| `GET /metrics` | None | Retrieval counters + total latency | None declared | 200; process-local |
| `GET /metrics/latency` | None | sample_count, p50_ms, p95_ms, p99_ms | None declared | 200; last 1000 successful retrievals per process |
| `POST /retrieve` | RetrieveRequest | RetrieveResponse | None declared | 200; invalid input 422; retrieval failure 503 |
| `POST /answer/evaluated` | EvaluatedAnswerRequest | EvaluatedAnswerResponse | None declared | 200; invalid input 422; supported upstream failures 503 |
| `POST /answer` | RetrieveRequest | AnswerResponse | None declared | 200; invalid input 422; supported upstream failures 503 |
| `POST /feedback` | FeedbackRequest | FeedbackRecord | None declared | 201; conflict 409; invalid input 422; storage failure 503 |
| `GET /feedback` | limit: 1–100, default 20 | list[FeedbackRecord] | FeedbackReviewer bearer | 200; invalid/missing credentials 401; invalid query 422; unconfigured/store failure 503 |
| `POST /feedback/{feedback_id}/review` | UUID path + FeedbackReview | {status: accepted / rejected} | FeedbackReviewer bearer | 200; credential failure 401; absent/already reviewed 409; invalid input 422; configuration/storage failure 503 |

### Agent application

| Method and path | Input | Output | Authentication | Outcomes / conditions |
|---|---|---|---|---|
| `GET /health` | None | {status: ok} | None declared | 200; liveness only |
| `GET /metrics` | None | agent_requests_total, agent_completed_total | None declared | 200; process-local |
| `POST /agent` | AgentRequest | AgentResponse | None declared | 200 for semantic outcomes; invalid input 422; upstream/schema/deadline failure 503 |

### Request examples

These examples illustrate the declared contracts; they were not sent to a running service.

```json
{
  "query": "What is the home loan processing fee?",
  "as_of": "2026-10-01",
  "product_id": "NEXA-HL",
  "jurisdiction": "IN",
  "top_k": 5
}
```

This policy payload is valid for `/retrieve`, `/answer` and `/agent`. `/answer/evaluated` additionally accepts `reference_answer`. AgentRequest also supports optional `customer_id` and one of `createCase`, `addCaseNote`, `escalateCase`, `createServiceRequest`; those action branches currently return clarification or unavailable, and never execute banking actions.

## Request and evidence flows

1. **Direct policy answer:** Streamlit/direct caller → `/answer` → `answer_policy` → shared answer Runnable → `retrieve_policy` → Atlas search, parent expansion and full linked amendments → context packing → structured answer draft → exact quote/citation validation → JSON response.
2. **Agent policy answer:** `/agent` → structured IntentDecision → required-scope/conflict checks → one HTTP `POST /retrieve` → status/strict-schema/as_of validation → retained RetrieveResponse in AgentState → `build_answer_chain(RunnableLambda(replay), llm, settings)` → AgentResponse → END. No second network/database retrieval occurs during answer generation, including citation-repair retry.
3. **Early agent exits:** forbidden wins immediately; missing or conflicting scope requests clarification. Customer-context and supported-action branches are unavailable after their required-scope checks. Neither these exits nor clarification/refusal invoke retrieval or grounded generation.
4. **Evaluated answer:** `/answer/evaluated` retrieves once, generates once (subject to existing quote-validation retry), and scores the exact packed contexts. Precision/recall require a supplied or exact-match golden reference. Optional telemetry failure preserves the answer/scores.
5. **Feedback:** submit stores an institution-scoped idempotent record; optional Datadog thumbs join the answer span. Authorized review transitions a pending record to accepted/rejected and does not modify policy or training data.
6. **Ingestion:** authoritative register → parser → clause/table chunks → scope metadata/stable IDs/checksums → compare existing children → embed changed children → upsert children and parents → stale cleanup. Explicit retirement is gated against still-authoritative register entries.

## Core contracts

| Contract | Fields / behavior |
|---|---|
| RetrieveRequest | query 1–2000 chars; as_of date required; top_k 1–20/default 5; optional nonblank product_id and jurisdiction |
| RetrieveResponse | as_of, results, amendments, timings; evidence property prioritizes complete amendments and suppresses duplicate ordinary hits by document/version |
| RetrieveHit | rank, score, child text, full parent_text, Citation |
| Citation | doc_id, title, policy_version, nullable clause, effective_date |
| RetrieveTimings | search_ms, parent_ms, total_ms |
| AnswerDraft | status, answer and exact EvidenceQuote items with evidence_id and quote |
| AnswerResponse | as_of; answered/insufficient_evidence/needs_clarification; answer; resolved citations; retrieval_timings; generation_ms; optional datadog_span_id |
| AgentRequest | query; optional as_of/product/customer/action/jurisdiction; top_k; customer_id must match NXC-0000 shape |
| IntentDecision | intent, extracted scope, product_required and missing_fields; scope conflicts force clarification |
| AgentResponse | intent; answered/insufficient_evidence/needs_clarification/forbidden/unavailable; message; missing_fields; optional AnswerResponse |
| EvaluatedAnswerResponse | answer plus AnswerQuality with four named metric statuses, optional values, reference source, timestamp and Datadog delivery metadata |
| FeedbackRequest / Record | original request+response with matching dates, helpful, submitter/submission UUIDs, correction; stored feedback_id, timestamp, pending/accepted/rejected status and review metadata |
| FeedbackReview | accepted/rejected status, nonblank reviewer and review_note |
| IngestRequest / Response | source identity/version/effectivity/corpus metadata; output chunk identities, changed/unchanged counts and embedding model |

All shared API models use Pydantic v2 with extra fields forbidden. Full machine-readable schemas and per-operation parameter declarations are in the two OpenAPI files.

## Every runtime Python module

Package `__init__.py` markers are omitted. Declaration names and line ranges below come from AST parsing of the frozen source snapshot; a module is listed even when it is an optional teaching or diagnostic tool.

| Module | Responsibility | Public declarations |
|---|---|---|
| [app/agent_main.py](source-snapshot/app/agent_main.py) | Separate Agent FastAPI app; reuses the common lifespan and registers only agent/operations routes. | `create_agent_app` (L9–13) |
| [app/agents/orchestrator.py](source-snapshot/app/agents/orchestrator.py) | Agent state, scope conflict resolution, conditional routing and terminal states. | `AgentState` (L15–20), `build_agent_graph` (L23–160) |
| [app/api/agent.py](source-snapshot/app/api/agent.py) | POST /agent, agent counters, bounded upstream httpx client, and safe 503 handling. | `metrics` (L24–28), `rag_client` (L31–39), `agent` (L43–60) |
| [app/api/answer.py](source-snapshot/app/api/answer.py) | Thin /answer and /answer/evaluated routers calling their services. | `evaluated_answer` (L25–40), `answer` (L44–59) |
| [app/api/auth.py](source-snapshot/app/api/auth.py) | Feedback reviewer bearer-token dependency with constant-time comparison. | `require_reviewer` (L14–28) |
| [app/api/feedback.py](source-snapshot/app/api/feedback.py) | Submit/list/review feedback, review dependency and conflict handling. | `submit` (L19–25), `list_recent` (L29–35), `review` (L39–48) |
| [app/api/operations.py](source-snapshot/app/api/operations.py) | Liveness, process-local retrieval counters and latency percentiles. | `health` (L12–13), `metrics` (L17–23), `latency_metrics` (L27–29) |
| [app/api/retrieval.py](source-snapshot/app/api/retrieval.py) | Thin /retrieve router calling retrieve_policy and sanitizing retrieval failures. | `retrieve` (L17–24) |
| [app/chains/answer.py](source-snapshot/app/chains/answer.py) | Grounded Runnable, evidence assembly, bounded quote-validation retry and answer statuses. | `build_answer_chain` (L24–113) |
| [app/chains/chunking.py](source-snapshot/app/chains/chunking.py) | Clause/section-aware chunk records; whole tables and bounded narrative splitting. | `Chunk` (L14–22), `chunk_by_clause` (L34–95) |
| [app/chains/context.py](source-snapshot/app/chains/context.py) | Token encoder, whole-parent/child packing, context deduplication and evidence JSON. | `token_encoder` (L12–13), `render_context` (L16–27), `assemble_context` (L30–60) |
| [app/chains/embeddings.py](source-snapshot/app/chains/embeddings.py) | Shared OpenAI embedding model, dimensions and batch settings for reading and writing. | `get_embeddings` (L8–15) |
| [app/chains/ingestion.py](source-snapshot/app/chains/ingestion.py) | LCEL parse/chunk/enrich/checksum/compare/embed/upsert pipeline with stable source identities. | `parent_key_prefix` (L20–21), `chunk_checksum` (L24–30), `build_ingestion_chain` (L33–150) |
| [app/chains/llm.py](source-snapshot/app/chains/llm.py) | Configured ChatOpenAI Responses API client, 60s timeout, one retry and token callback. | `get_chat_model` (L9–17) |
| [app/chains/parsing.py](source-snapshot/app/chains/parsing.py) | Born-digital PDF parsing with pdfplumber and unstructured fallback for other document types. | `parse_document` (L14–18) |
| [app/chains/prompts/answer.py](source-snapshot/app/chains/prompts/answer.py) | Versioned grounded-answer prompt and citation/scope rules. | Module constants / entry-point invocation |
| [app/chains/prompts/judge.py](source-snapshot/app/chains/prompts/judge.py) | Versioned structured evaluation judge prompt. | Module constants / entry-point invocation |
| [app/chains/prompts/orchestrator.py](source-snapshot/app/chains/prompts/orchestrator.py) | Versioned intent classifier prompt, permitted scope and forbidden-request priority. | Module constants / entry-point invocation |
| [app/chains/prompts/rerank.py](source-snapshot/app/chains/prompts/rerank.py) | Query/document/date reranker prompt construction. | `rerank_prompt` (L4–20) |
| [app/chains/rerank.py](source-snapshot/app/chains/rerank.py) | Optional HTTP pair scoring, logprob validation and descending relevance sort. | `relevance_probability` (L16–22), `completion_probabilities` (L25–43), `build_rerank_chain` (L46–103) |
| [app/chains/retrieval.py](source-snapshot/app/chains/retrieval.py) | Scoped search, parent validation, optional reranking, linked amendment expansion and timings. | `build_retrieval_chain` (L24–149) |
| [app/core/config.py](source-snapshot/app/core/config.py) | Cached Pydantic Settings, UISettings and AgentSettings; secrets and config bounds. | `Settings` (L10–61), `get_settings` (L65–66), `UISettings` (L69–73), `get_ui_settings` (L77–78), `AgentSettings` (L81–86), `get_agent_settings` (L90–91) |
| [app/core/logging.py](source-snapshot/app/core/logging.py) | JSON structlog processors, timestamps, filtering and exception rendering. | `configure_logging` (L8–19) |
| [app/core/observability.py](source-snapshot/app/core/observability.py) | Versioned prompt annotations, bounded latency samples and token-usage callbacks. | `prompt_annotation_context` (L18–44), `latency_summary` (L47–52), `TokenUsageLogger` (L55–61) |
| [app/core/telemetry.py](source-snapshot/app/core/telemetry.py) | Optional ddtrace.patch_all; startup-before-import guidance for ddtrace-run. | `init_telemetry` (L4–14) |
| [app/database/diagnostics.py](source-snapshot/app/database/diagnostics.py) | Read-only chunk/parent/index snapshots for teaching diagnostics; vectors replaced by lengths. | `read_rag_snapshot` (L13–48) |
| [app/database/feedback.py](source-snapshot/app/database/feedback.py) | Institution-scoped feedback upsert/read and pending-only review transition. | `save_feedback` (L12–35), `list_feedback` (L38–45), `review_feedback` (L48–53) |
| [app/database/mongo.py](source-snapshot/app/database/mongo.py) | Cached PyMongo client, Atlas vector store, upserting parent docstore, stale deletion and retirement. | `get_vector_store` (L27–40), `UpsertingParentStore` (L43–62), `get_parent_store` (L65–67), `delete_stale_chunks` (L70–73), `retire_document` (L76–90) |
| [app/database/retrieval.py](source-snapshot/app/database/retrieval.py) | Scoped complete-amendment traversal, Atlas hybrid retriever and golden-reference text resolution. | `build_amendment_search` (L16–82), `build_hybrid_search` (L85–101), `resolve_reference_contexts` (L104–121) |
| [app/evaluation/answer_evaluation.py](source-snapshot/app/evaluation/answer_evaluation.py) | Golden-answer/evidence records, exact source capture and mechanical grounding checks. | `ExpectedEvidence` (L16–21), `GoldenAnswer` (L24–30), `EvidenceContext` (L33–37), `EvaluationRecord` (L40–46), `load_golden` (L49–57), `capture_sources` (L60–67), `mechanical_checks` (L70–104) |
| [app/evaluation/check_reranker.py](source-snapshot/app/evaluation/check_reranker.py) | Configured reranker availability and scoring sanity check CLI. | `check` (L19–50), `main` (L53–65) |
| [app/evaluation/failure_demo.py](source-snapshot/app/evaluation/failure_demo.py) | Offline demonstration report for expected grounding failures. | `demo_report` (L18–103) |
| [app/evaluation/live.py](source-snapshot/app/evaluation/live.py) | Four concurrent RAGAS metrics, 120s bounds and per-metric unavailable/error isolation. | `score_answer` (L17–84) |
| [app/evaluation/rag_failure_examples.py](source-snapshot/app/evaluation/rag_failure_examples.py) | Teaching reports using indexed source snapshots, selected failure examples and comparisons. | `example_report` (L87–400), `main` (L403–413) |
| [app/evaluation/rag_failure_modes.py](source-snapshot/app/evaluation/rag_failure_modes.py) | Diagnostic models and checks for retrieval, context, parent linkage, staleness and embeddings. | `EvidenceRef` (L17–21), `ChunkSnapshot` (L24–32), `diagnose_retrieval` (L35–55), `diagnose_expanded_context` (L63–103), `diagnose_parent_links` (L106–147), `diagnose_staleness` (L157–180), `diagnose_embeddings` (L183–200), `demo_report` (L203–273), `main` (L276–278) |
| [app/evaluation/ragas_metrics.py](source-snapshot/app/evaluation/ragas_metrics.py) | StructuredJudge and embedding adapters for the four RAGAS collection metrics. | `StructuredJudge` (L15–31), `MetricEmbeddings` (L34–43), `RagasScorer` (L46–54) |
| [app/evaluation/run.py](source-snapshot/app/evaluation/run.py) | Golden-case loading, one-answer capture, structured judge, RAGAS, optional score gate and report CLI. | `GoldenCase` (L35–43), `JudgeScore` (L46–51), `load_cases` (L54–62), `trace_summary` (L65–79), `collect_records` (L82–163), `evaluate_ragas` (L166–208), `quality_gate` (L211–224), `publish_datadog_evaluations` (L227–258), `run` (L261–291), `main` (L294–344) |
| [app/main.py](source-snapshot/app/main.py) | RAG FastAPI app factory, router registration, logging/telemetry/tokenizer lifespan. | `lifespan` (L20–25), `create_app` (L28–34) |
| [app/models/agent.py](source-snapshot/app/models/agent.py) | AgentRequest, IntentDecision, AgentResponse and intent/action/missing-field literal types. | `AgentRequest` (L17–26), `IntentDecision` (L29–40), `AgentResponse` (L43–52) |
| [app/models/answer.py](source-snapshot/app/models/answer.py) | Structured draft, exact evidence quote, resolved citation and API answer models. | `EvidenceQuote` (L11–15), `AnswerDraft` (L18–25), `AnswerCitation` (L28–30), `AnswerResponse` (L33–42) |
| [app/models/evaluation.py](source-snapshot/app/models/evaluation.py) | Evaluated answer schemas, named metric statuses and finite bounded quality scores. | `EvaluatedAnswerRequest` (L20–21), `QualityScore` (L24–47), `AnswerQuality` (L50–64), `EvaluatedAnswerResponse` (L67–71) |
| [app/models/feedback.py](source-snapshot/app/models/feedback.py) | Feedback submission/record/review schemas and matching lookup-date validation. | `FeedbackRequest` (L13–27), `FeedbackRecord` (L30–35), `FeedbackReview` (L38–43) |
| [app/models/ingestion.py](source-snapshot/app/models/ingestion.py) | Document metadata input and ingestion outcome contracts. | `IngestRequest` (L8–28), `IngestResponse` (L31–39) |
| [app/models/retrieval.py](source-snapshot/app/models/retrieval.py) | RetrieveRequest, Citation, RetrieveHit, RetrieveTimings, RetrieveResponse and complete evidence property. | `RetrieveRequest` (L8–15), `Citation` (L18–25), `RetrieveHit` (L28–35), `RetrieveTimings` (L38–43), `RetrieveResponse` (L46–61) |
| [app/services/agent.py](source-snapshot/app/services/agent.py) | Build classifier and bounded graph; replay retained evidence into the existing answer chain. | `orchestrate` (L31–71) |
| [app/services/agent_retrieval.py](source-snapshot/app/services/agent_retrieval.py) | HTTP-only retrieval adapter; POST, status/schema validation and lookup-date equality. | `retrieve_over_http` (L8–17) |
| [app/services/answer.py](source-snapshot/app/services/answer.py) | Run the grounded chain, log completion and join an optional Datadog workflow span. | `answer_policy` (L19–48) |
| [app/services/evaluation.py](source-snapshot/app/services/evaluation.py) | Resolve optional golden reference; generate once, score exact evidence and publish joined metrics. | `answer_with_quality` (L27–128) |
| [app/services/feedback.py](source-snapshot/app/services/feedback.py) | Deterministic idempotent feedback, worker-thread persistence, optional Datadog feedback. | `submit_feedback` (L15–47), `list_recent` (L50–51), `review` (L54–55) |
| [app/services/ingestion.py](source-snapshot/app/services/ingestion.py) | Authoritative-register ingestion CLI, stale-chunk cleanup and explicit document retirement. | `requests_from_register` (L28–47), `ingest` (L50–73), `main` (L76–92) |
| [app/services/retrieval.py](source-snapshot/app/services/retrieval.py) | Compose vector/parent stores, dense/hybrid search, optional reranking and amendment loading. | `retrieve_policy` (L20–48) |
| [app/streamlit_app.py](source-snapshot/app/streamlit_app.py) | Streamlit entry point delegating to app.ui.app.main. | Module constants / entry-point invocation |
| [app/ui/app.py](source-snapshot/app/ui/app.py) | Cached API client, local chat state, source/citation rendering, quality display, feedback and reviewer UI. | `api_client` (L19–20), `show_answer` (L23–34), `feedback_form` (L37–62), `review_feedback` (L65–116), `open_chat` (L119–121), `send_question` (L124–157), `show_turn` (L160–203), `main` (L206–393) |

## Persistence, scope and retrieval options

- `MONGODB_COLLECTION`: children, text, embeddings, document metadata, checksum, parent_id and amendment links. Exact collection name is required configuration, not hard-coded.
- `MONGODB_PARENT_COLLECTION`: full unembedded sections, default `policy_sections`.
- `MONGODB_FEEDBACK_COLLECTION`: institution-scoped submissions and pending-only review records, default `policy_feedback`.
- Atlas vector index defaults `policy_chunks_v1`; optional text index defaults `policy_text_v1`. Definitions are [documented in source](source-snapshot/app/database/indexes.md); search indexes are not auto-created.
- Retrieval filters institution, jurisdiction, confidentiality and inclusive `effective_date <= as_of <= effective_to_search`; optional product adds a restriction. Open-ended source metadata uses a search sentinel of `9999-12-31`.
- Dense retrieval is the default. Hybrid BM25+vector retrieval uses RRF and the same corpus restrictions. Reranking is separately opt-in.
- Full linked circulars follow supersedes recursively and remain outside ordinary top_k. Inconsistent chunk scope fails closed. Entirely missing amendment chunks cannot be detected without an ingestion manifest.
- Whole parents/children are packed within `CONTEXT_MAX_TOKENS` (default 6000); mandatory amendment truncation is rejected. At most two answer drafts are attempted for invalid quote/citation structure.

## Configuration and execution

| Setting / group | Code default or requirement |
|---|---|
| Python / package manager | Python >=3.14; uv |
| Required Settings | mongodb_uri, mongodb_db, mongodb_collection, openai_api_key, institution, jurisdiction, confidentiality_level |
| Chat | chat_model=gpt-6-luna; ChatOpenAI Responses API; 60s timeout and max_retries=1 |
| Embeddings | text-embedding-3-small; 1536 dimensions; batch size 100 |
| Retrieval | dense; top_k default 5; rerank_enabled=false; retrieval_candidates=20 |
| Reranking | Ollama by default; http://127.0.0.1:11434; nexaassist-reranker:0.6b-mlx; 4000-token prompt limit |
| Chunking | max 1200 chars; overlap 150 chars; full tables are retained |
| UI | api_base_url=http://127.0.0.1:8000; timezone Asia/Kolkata; HTTP answer timeout 180s/evaluated timeout 300s |
| Agent | rag_base_url=http://127.0.0.1:8000/; HTTP timeout 60s, total run 180s, redirects false, graph recursion limit 8 |
| Reviewer | optional feedback_reviewer_token, minimum 32 chars; unconfigured review is disabled |
| Telemetry | dd_trace_enabled=false; dd_service=nexaassist-api; dd_site=datadoghq.com; SDK reads process DD_* environment |

Values here are source defaults, not inspected `.env` values or guarantees of provider support.

```sh
uv run uvicorn app.main:app --port 8000
uv run uvicorn app.agent_main:app --port 8001
uv run streamlit run app/streamlit_app.py
uv run python -m app.services.ingestion nexa_synthetic_data/document_register.json
uv run python -m app.evaluation.run --dataset evaluation/datasets/answer.jsonl --output app/evaluation/results/latest.json
uv run pytest
uv run ruff check .
uv run mypy .
```

Port 8001 is an example for running both apps locally. For Datadog APM, launch with `ddtrace-run` after loading the required DD_* values into the process environment. The commands above are usage examples; this architecture task did not launch the apps or run ingestion/evaluations.

## Deployment and telemetry

- [Dockerfile](source-snapshot/app/Dockerfile) builds a Python 3.14 RAG image, installs the evaluation extra, exposes 8000 and starts `ddtrace-run uvicorn app.main:app`. It does not start the Agent Service, Streamlit or Atlas.
- [Datadog compose](source-snapshot/app/compose.datadog.yaml) starts only the Datadog Agent and maps host 18126→8126 TCP / 18125→8125 UDP. It does not define the application network or deploy an Atlas cluster.
- Common lifespan calls optional ddtrace.patch_all, configures JSON structlog and warms the tokenizer. Start instrumentation before app creation when APM is required.
- Prompt annotations, token callbacks, workflow spans and joined RAGAS/user-feedback scores exist. Datadog collection/export depends on enabled runtime configuration and was not tested here.
- `/health` is liveness, not an OpenAI/Atlas connectivity check. Counters and percentile samples are process-local, not aggregated across workers.

## Standalone banking mock APIs

The mock reads synthetic fixtures at startup and stores writes in process memory. It is not connected to Agent Service. Any nonempty bearer token is accepted as a mock caller identity; this is not production authentication. Write idempotency is scoped by caller/method/path/key for 24 hours. ETag/If-Match gates apply where the handler implements them.

| Method and path | Handler | Source |
|---|---|---|
| `GET /v1/customers/{customerId}` | `get_profile` | L79–82 |
| `GET /v1/customers/{customerId}/accounts` | `list_accounts` | L85–89 |
| `GET /v1/accounts/{accountId}/transactions` | `list_transactions` | L92–102 |
| `GET /v1/customers/{customerId}/kyc-status` | `get_kyc` | L105–107 |
| `GET /v1/customers/{customerId}/bureau-summary` | `get_bureau` | L110–113 |
| `GET /v1/customers/{customerId}/income` | `get_income` | L116–120 |
| `GET /v1/customers/{customerId}/applications` | `get_apps` | L123–125 |
| `POST /v1/cases` | `create_case` | L200–209 |
| `GET /v1/cases/{caseId}` | `get_case` | L223–226 |
| `POST /v1/cases/{caseId}/notes` | `add_note` | L229–237 |
| `POST /v1/cases/{caseId}/escalations` | `escalate` | L240–250 |
| `POST /v1/service-requests` | `service_request` | L253–272 |
| `POST /_mock/reset` | `reset` | L275–280 |

Full declared mock contract: [OpenAPI YAML](source-snapshot/nexa_synthetic_data/api/nexabank_case_core_api.openapi.yaml). Concrete routes in the table come from server.py, including mock-only controls. No customer records are copied into the documentation snapshot.

## Tests, supporting assets and implementation limits

| Area | Existing evidence |
|---|---|
| Agent | tests/test_agent.py: fake models, ASGI/HTTP transports, one-retrieval handoff, full amendments/citations, safe failures, terminal routes, bounded client and graph deadline |
| RAG | tests/test_retrieval.py, test_answer.py, test_hybrid_rerank.py, test_amendments.py |
| Quality / feedback | tests/test_evaluation.py, test_live_evaluation.py, test_feedback.py |
| Infrastructure / UI | tests/test_telemetry.py, test_ui.py, test_ingestion.py |
| Teaching / architecture | tests/test_rag_failure_modes.py, test_architecture_document.py; notebooks and pre-existing architecture documents are supporting material |
| Golden datasets | evaluation/datasets/ answer/retrieval/agent JSONL; local quality references, not vector databases |

- Actual LangGraph support now exists even though AGENTS.md still describes the graph layer as future work.
- Agent customer-context reads, banking actions, Validator/Action stages and FastMCP remain unimplemented. The presence of a mock server or dependency does not connect them.
- No token-streaming response path is implemented. Responses are JSON.
- Ingestion writes multiple collections without a transaction; concurrent ingestion and partial failures need that limitation considered.
- Structured routing remains model-dependent. Quote validation confirms quotes and source markers, not the truth of every inference.
- Document parser supports born-digital PDFs; scanned PDFs/OCR are not established by this implementation.
- The architecture maps source-level behavior. No production traffic, live providers, infrastructure health, latency benchmark or telemetry export was checked.

## Existing modified and untracked paths

These paths were present when the documentation snapshot was captured. Existing work was preserved; only this new `.archify/architecture-nexaassist-20261024-215323/` artifact folder was authored for this request.

```text
 M .env.example
 M AGENTS.md
 M APP_COMPONENT_GUIDE.md
 M CLAUDE.md
 M DATADOG_README.md
 M README.md
 M app/.streamlit/config.toml
 M app/api/feedback.py
 M app/chains/answer.py
 M app/chains/context.py
 M app/chains/prompts/answer.py
 M app/chains/prompts/judge.py
 M app/chains/retrieval.py
 M app/core/config.py
 M app/core/observability.py
 M app/database/feedback.py
 M app/database/indexes.md
 M app/database/retrieval.py
 M app/evaluation/answer_evaluation.py
 M app/evaluation/live.py
 M app/evaluation/rag_failure_examples.py
 M app/evaluation/run.py
 M app/models/answer.py
 M app/models/feedback.py
 M app/models/retrieval.py
 M app/services/answer.py
 M app/services/evaluation.py
 M app/services/feedback.py
 M app/services/retrieval.py
 M app/ui/app.py
 M evaluation/datasets/answer.jsonl
 M nexa_synthetic_data/golden_qa/golden_qa.json
 M nexa_synthetic_data/golden_qa/golden_qa.jsonl
 M pyproject.toml
 M requirements.txt
 M tests/test_answer.py
 M tests/test_evaluation.py
 M tests/test_feedback.py
 M tests/test_hybrid_rerank.py
 M tests/test_retrieval.py
 M tests/test_telemetry.py
 M tests/test_ui.py
 M uv.lock
?? .agents/
?? .archify/
?? .planning/
?? .streamlit/
?? "1. Phase1_Enterprise_RAG_Agentic-AI_MCP_Evaluations_Full_Syllabus-.pdf"
?? C4-Documentation/
?? DATADOG_FIELD_GUIDE.html
?? DEVELOPMENT_TOOLING_GUIDE.md
?? FIX_REPORT.md
?? PROMPT_HISTORY_AND_GUIDE.md
?? app/agent_main.py
?? app/agents/
?? app/api/agent.py
?? app/api/auth.py
?? app/chains/prompts/orchestrator.py
?? app/evaluation/results/
?? app/models/agent.py
?? app/services/agent.py
?? app/services/agent_retrieval.py
?? codebase-recon-report.md
?? evaluation/datasets/agent.jsonl
?? nexa_synthetic_data/README.md
?? nexa_synthetic_data/_clause_registry.json
?? nexa_synthetic_data/build_all.sh
?? nexa_synthetic_data/policies/NexaDrive_Auto_Loan_Training_Companion.pdf
?? nexa_synthetic_data/policies/NexaFlex_Personal_Loan_Training_Companion.pdf
?? nexa_synthetic_data/policies/NexaHome_Loan_Training_Companion_2026.pdf
?? nexa_synthetic_data/uploads/
?? notebooks/
?? skills-lock.json
?? tests/test_agent.py
?? tests/test_amendments.py
?? tests/test_architecture_document.py
```
