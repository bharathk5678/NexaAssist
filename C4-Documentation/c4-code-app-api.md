# C4 code inventory: app/api

**Language:** Python 3.14. **Scope:** direct modules listed below, with child inventories linked separately.

Thin REST adapters for policy answers, evidence retrieval, operational endpoints and feedback review. Provider exceptions become HTTP responses; routers do not define chains.

**Location:** [app/api](../app/api)

## Observability and evaluation relevance

/metrics and /metrics/latency return process-local JSON. /health is a liveness response, not a dependency readiness check. HTTP tracing comes from instrumentation.

## Module `__init__.py`

**Source:** [app/api/__init__.py](../app/api/__init__.py)

**Internal dependencies:** None.

**External / standard-library dependencies:** None.

No top-level functions or classes; module provides the exports above or a package marker.

## Module `answer.py`

**Source:** [app/api/answer.py:1](../app/api/answer.py#L1)

**Internal dependencies:** `app.core.config.Settings`, `app.core.config.get_settings`, `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveRequest`, `app.services.answer.answer_policy`

**External / standard-library dependencies:** `fastapi.APIRouter`, `fastapi.Depends`, `fastapi.HTTPException`, `httpx`, `langchain_core.exceptions.OutputParserException`, `langchain_openai.chat_models.base.OpenAIRefusalError`, `openai.OpenAIError`, `pymongo.errors.PyMongoError`, `structlog`, `typing.Annotated`

**Module state / exports:** `router`, `logger`.

### `answer`

```python
async def answer(request: RetrieveRequest, settings: Annotated[Settings, Depends(get_settings)]) -> AnswerResponse
```

**Source:** [app/api/answer.py:23](../app/api/answer.py#L23)

Answer; behavior is defined by the linked implementation.

**Decorators:** `router.post('/answer')`.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.core.config.get_settings`, `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveRequest`, `app.services.answer.answer_policy`, `fastapi.Depends`, `fastapi.HTTPException`, `httpx`, `langchain_core.exceptions.OutputParserException`, `langchain_openai.chat_models.base.OpenAIRefusalError`, `openai.OpenAIError`, `pymongo.errors.PyMongoError`, `typing.Annotated`

**Other calls / relationships:** `logger.error`, `router.post`, `type`.

## Module `feedback.py`

**Source:** [app/api/feedback.py:1](../app/api/feedback.py#L1)

**Internal dependencies:** `app.core.config.Settings`, `app.core.config.get_settings`, `app.models.feedback.FeedbackRecord`, `app.models.feedback.FeedbackRequest`, `app.models.feedback.FeedbackReview`, `app.services.feedback`

**External / standard-library dependencies:** `fastapi.APIRouter`, `fastapi.Depends`, `fastapi.HTTPException`, `fastapi.Query`, `pymongo.errors.PyMongoError`, `typing.Annotated`, `uuid.UUID`

**Module state / exports:** `router`, `ConfiguredSettings`.

### `submit`

```python
async def submit(request: FeedbackRequest, settings: ConfiguredSettings) -> FeedbackRecord
```

**Source:** [app/api/feedback.py:18](../app/api/feedback.py#L18)

Submit; behavior is defined by the linked implementation.

**Decorators:** `router.post('/feedback', status_code=201)`.

**Imported dependencies referenced:** `app.models.feedback.FeedbackRecord`, `app.models.feedback.FeedbackRequest`, `app.services.feedback`, `fastapi.HTTPException`, `pymongo.errors.PyMongoError`

**Other calls / relationships:** `router.post`.

### `list_recent`

```python
async def list_recent(settings: ConfiguredSettings, limit: Annotated[int, Query(ge=1, le=100)]=20) -> list[FeedbackRecord]
```

**Source:** [app/api/feedback.py:26](../app/api/feedback.py#L26)

List recent; behavior is defined by the linked implementation.

**Decorators:** `router.get('/feedback')`.

**Imported dependencies referenced:** `app.models.feedback.FeedbackRecord`, `app.services.feedback`, `fastapi.HTTPException`, `fastapi.Query`, `pymongo.errors.PyMongoError`, `typing.Annotated`

**Other calls / relationships:** `router.get`.

### `review`

```python
async def review(feedback_id: UUID, request: FeedbackReview, settings: ConfiguredSettings) -> dict[str, str]
```

**Source:** [app/api/feedback.py:36](../app/api/feedback.py#L36)

Review; behavior is defined by the linked implementation.

**Decorators:** `router.post('/feedback/{feedback_id}/review')`.

**Imported dependencies referenced:** `app.models.feedback.FeedbackReview`, `app.services.feedback`, `fastapi.HTTPException`, `pymongo.errors.PyMongoError`, `uuid.UUID`

**Other calls / relationships:** `router.post`.

## Module `operations.py`

**Source:** [app/api/operations.py:1](../app/api/operations.py#L1)

**Internal dependencies:** `app.core.observability.latency_summary`, `app.services.retrieval.retrieval_metrics`

**External / standard-library dependencies:** `fastapi.APIRouter`

**Module state / exports:** `router`.

### `health`

```python
async def health() -> dict[str, str]
```

**Source:** [app/api/operations.py:12](../app/api/operations.py#L12)

Health; behavior is defined by the linked implementation.

**Decorators:** `router.get('/health')`.

**Imported dependencies referenced:** None directly.

**Other calls / relationships:** `router.get`.

### `metrics`

```python
async def metrics() -> dict[str, int | float]
```

**Source:** [app/api/operations.py:17](../app/api/operations.py#L17)

Metrics; behavior is defined by the linked implementation.

**Decorators:** `router.get('/metrics')`.

**Imported dependencies referenced:** `app.services.retrieval.retrieval_metrics`

**Other calls / relationships:** `router.get`.

### `latency_metrics`

```python
async def latency_metrics() -> dict[str, int | float]
```

**Source:** [app/api/operations.py:27](../app/api/operations.py#L27)

Nearest-rank percentiles of the last 1000 successful requests in this process.

**Decorators:** `router.get('/metrics/latency')`.

**Imported dependencies referenced:** `app.core.observability.latency_summary`

**Other calls / relationships:** `router.get`.

## Module `retrieval.py`

**Source:** [app/api/retrieval.py:1](../app/api/retrieval.py#L1)

**Internal dependencies:** `app.core.config.Settings`, `app.core.config.get_settings`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.services.retrieval.retrieve_policy`

**External / standard-library dependencies:** `fastapi.APIRouter`, `fastapi.Depends`, `fastapi.HTTPException`, `structlog`, `typing.Annotated`

**Module state / exports:** `router`, `logger`.

### `retrieve`

```python
async def retrieve(request: RetrieveRequest, settings: Annotated[Settings, Depends(get_settings)]) -> RetrieveResponse
```

**Source:** [app/api/retrieval.py:17](../app/api/retrieval.py#L17)

Retrieve; behavior is defined by the linked implementation.

**Decorators:** `router.post('/retrieve')`.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.core.config.get_settings`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.services.retrieval.retrieve_policy`, `fastapi.Depends`, `fastapi.HTTPException`, `typing.Annotated`

**Other calls / relationships:** `logger.exception`, `router.post`.
