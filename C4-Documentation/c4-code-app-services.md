# C4 code inventory: app/services

**Language:** Python 3.14. **Scope:** direct modules listed below, with child inventories linked separately.

Business orchestration between routers and chains/database adapters. Retrieval metrics and JSON completion logs are emitted here; ingestion also has a CLI.

**Location:** [app/services](../app/services)

## Observability and evaluation relevance

retrieval_metrics is an in-memory Counter per process. answer_completed records generation time and citation count. The ordinary retrieval service does not pass hybrid-search or reranker adapters into build_retrieval_chain.

## Module `__init__.py`

**Source:** [app/services/__init__.py](../app/services/__init__.py)

**Internal dependencies:** None.

**External / standard-library dependencies:** None.

No top-level functions or classes; module provides the exports above or a package marker.

## Module `answer.py`

**Source:** [app/services/answer.py:1](../app/services/answer.py#L1)

**Internal dependencies:** `app.chains.answer.build_answer_chain`, `app.chains.llm.get_chat_model`, `app.core.config.Settings`, `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.services.retrieval.retrieve_policy`

**External / standard-library dependencies:** `langchain_core.runnables.RunnableLambda`, `structlog`

**Module state / exports:** `logger`.

### `answer_policy`

```python
async def answer_policy(request: RetrieveRequest, settings: Settings) -> AnswerResponse
```

**Source:** [app/services/answer.py:16](../app/services/answer.py#L16)

Answer policy; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.chains.answer.build_answer_chain`, `app.chains.llm.get_chat_model`, `app.core.config.Settings`, `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.services.retrieval.retrieve_policy`, `langchain_core.runnables.RunnableLambda`

**Other calls / relationships:** `chain.ainvoke`, `len`, `logger.info`.

### `answer_policy.retrieve`

```python
async def retrieve(value: RetrieveRequest) -> RetrieveResponse
```

**Source:** [app/services/answer.py:17](../app/services/answer.py#L17)

Retrieve; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.services.retrieval.retrieve_policy`

## Module `feedback.py`

**Source:** [app/services/feedback.py:1](../app/services/feedback.py#L1)

**Internal dependencies:** `app.core.config.Settings`, `app.database.feedback`, `app.models.feedback.FeedbackRecord`, `app.models.feedback.FeedbackRequest`, `app.models.feedback.FeedbackReview`

**External / standard-library dependencies:** `asyncio`, `datetime.UTC`, `datetime.datetime`, `uuid.UUID`, `uuid.uuid4`

### `submit_feedback`

```python
async def submit_feedback(request: FeedbackRequest, settings: Settings) -> FeedbackRecord
```

**Source:** [app/services/feedback.py:12](../app/services/feedback.py#L12)

Submit feedback; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.database.feedback`, `app.models.feedback.FeedbackRecord`, `app.models.feedback.FeedbackRequest`, `asyncio`, `datetime.UTC`, `datetime.datetime`, `uuid.uuid4`

**Other calls / relationships:** `request.model_dump`.

### `list_recent`

```python
async def list_recent(settings: Settings, limit: int) -> list[FeedbackRecord]
```

**Source:** [app/services/feedback.py:20](../app/services/feedback.py#L20)

List recent; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.database.feedback`, `app.models.feedback.FeedbackRecord`, `asyncio`

### `review`

```python
async def review(feedback_id: UUID, request: FeedbackReview, settings: Settings) -> bool
```

**Source:** [app/services/feedback.py:24](../app/services/feedback.py#L24)

Review; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.database.feedback`, `app.models.feedback.FeedbackReview`, `asyncio`, `uuid.UUID`

## Module `ingestion.py`

**Source:** [app/services/ingestion.py:1](../app/services/ingestion.py#L1)

**Internal dependencies:** `app.chains.embeddings.get_embeddings`, `app.chains.ingestion.build_ingestion_chain`, `app.core.config.Settings`, `app.core.config.get_settings`, `app.core.logging.configure_logging`, `app.core.telemetry.init_telemetry`, `app.database.mongo.delete_stale_chunks`, `app.database.mongo.get_parent_store`, `app.database.mongo.get_vector_store`, `app.database.mongo.retire_document`, `app.models.ingestion.IngestRequest`, `app.models.ingestion.IngestResponse`

**External / standard-library dependencies:** `argparse`, `asyncio`, `json`, `pathlib.Path`, `structlog`

**Module state / exports:** `logger`, `DOC_TYPES`.

### `requests_from_register`

```python
def requests_from_register(register_path: Path, settings: Settings) -> list[IngestRequest]
```

**Source:** [app/services/ingestion.py:28](../app/services/ingestion.py#L28)

One IngestRequest per authoritative document in document_register.json.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `json`, `pathlib.Path`

**Other calls / relationships:** `entry['doc_id'].split`, `register_path.read_text`, `str`.

### `ingest`

```python
async def ingest(requests: list[IngestRequest]) -> list[IngestResponse]
```

**Source:** [app/services/ingestion.py:50](../app/services/ingestion.py#L50)

Embed only new or changed chunks, then retire chunks the source no longer has.

**Imported dependencies referenced:** `app.chains.embeddings.get_embeddings`, `app.chains.ingestion.build_ingestion_chain`, `app.core.config.get_settings`, `app.database.mongo.delete_stale_chunks`, `app.database.mongo.get_parent_store`, `app.database.mongo.get_vector_store`, `app.models.ingestion.IngestRequest`, `app.models.ingestion.IngestResponse`, `asyncio`

**Other calls / relationships:** `chain.ainvoke`, `logger.info`, `request.effective_date.isoformat`, `responses.append`.

### `main`

```python
def main() -> None
```

**Source:** [app/services/ingestion.py:76](../app/services/ingestion.py#L76)

Ingest a register, or explicitly retire one document withdrawn from it.

**Imported dependencies referenced:** `app.core.config.get_settings`, `app.core.logging.configure_logging`, `app.core.telemetry.init_telemetry`, `app.database.mongo.retire_document`, `argparse`, `asyncio`, `json`, `pathlib.Path`

**Other calls / relationships:** `any`, `args.register.read_text`, `ingest`, `logger.info`, `parser.add_argument`, `parser.error`, `parser.parse_args`, `requests_from_register`.

## Module `retrieval.py`

**Source:** [app/services/retrieval.py:1](../app/services/retrieval.py#L1)

**Internal dependencies:** `app.chains.embeddings.get_embeddings`, `app.chains.retrieval.build_retrieval_chain`, `app.core.config.Settings`, `app.core.observability.retrieval_latencies`, `app.database.mongo.get_parent_store`, `app.database.mongo.get_vector_store`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`

**External / standard-library dependencies:** `collections.Counter`, `structlog`

**Module state / exports:** `logger`, `retrieval_metrics`.

### `retrieve_policy`

```python
async def retrieve_policy(request: RetrieveRequest, settings: Settings) -> RetrieveResponse
```

**Source:** [app/services/retrieval.py:18](../app/services/retrieval.py#L18)

Retrieve policy; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.chains.embeddings.get_embeddings`, `app.chains.retrieval.build_retrieval_chain`, `app.core.config.Settings`, `app.core.observability.retrieval_latencies`, `app.database.mongo.get_parent_store`, `app.database.mongo.get_vector_store`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`

**Other calls / relationships:** `chain.ainvoke`, `len`, `logger.info`, `logger.warning`, `request.as_of.isoformat`, `round`.
