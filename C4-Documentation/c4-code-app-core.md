# C4 code inventory: app/core

**Language:** Python 3.14. **Scope:** direct modules listed below, with child inventories linked separately.

Central environment-backed configuration, structured JSON logging, Datadog integration startup and local observation buffers.

**Location:** [app/core](../app/core)

## Observability and evaluation relevance

TokenUsageLogger logs usage_metadata when returned. Local latency samples are capped at 1,000 successful retrievals. configure_logging creates JSON output, not a log-forwarding transport.

## Module `__init__.py`

**Source:** [app/core/__init__.py](../app/core/__init__.py)

**Internal dependencies:** None.

**External / standard-library dependencies:** None.

No top-level functions or classes; module provides the exports above or a package marker.

## Module `config.py`

**Source:** [app/core/config.py:1](../app/core/config.py#L1)

**Internal dependencies:** None.

**External / standard-library dependencies:** `functools.lru_cache`, `pydantic.Field`, `pydantic.SecretStr`, `pydantic.model_validator`, `pydantic_settings.BaseSettings`, `pydantic_settings.SettingsConfigDict`, `typing.Literal`

### Class `Settings`

`class Settings(BaseSettings)` — [app/core/config.py:10](../app/core/config.py#L10)

Settings; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
mongodb_uri: SecretStr
mongodb_db: str
mongodb_collection: str
vector_index_name: str = 'policy_chunks_v1'
mongodb_parent_collection: str = 'policy_sections'
mongodb_feedback_collection: str = 'policy_feedback'
openai_api_key: SecretStr
embedding_model: str = 'text-embedding-3-small'
embedding_dimensions: int = Field(default=1536, gt=0)
embedding_batch_size: int = Field(default=100, ge=1, le=100)
chat_model: str = 'gpt-6-luna'
eval_judge_model: str | None = None
retrieval_mode: Literal['dense', 'hybrid'] = 'dense'
text_index_name: str = 'policy_text_v1'
retrieval_candidates: int = Field(default=20, ge=20, le=50)
rerank_enabled: bool = False
context_max_tokens: int = Field(default=6000, ge=256)
rerank_model: str = 'nexaassist-reranker:0.6b-mlx'
rerank_api: Literal['ollama', 'openai'] = 'ollama'
rerank_base_url: str = 'http://127.0.0.1:11434'
rerank_api_key: SecretStr = SecretStr('ollama')
rerank_max_tokens: int = Field(default=4000, ge=256)
token_encoding: str = 'o200k_base'
chunk_max_characters: int = Field(default=1200, gt=0)
chunk_overlap_characters: int = Field(default=150, ge=0)
institution: str
jurisdiction: str
confidentiality_level: str
log_level: str = 'INFO'
dd_trace_enabled: bool = False
```

### `Settings.valid_overlap`

```python
def valid_overlap(self) -> Settings
```

**Source:** [app/core/config.py:50](../app/core/config.py#L50)

Valid overlap; behavior is defined by the linked implementation.

**Decorators:** `model_validator(mode='after')`.

**Imported dependencies referenced:** `pydantic.model_validator`

**Other calls / relationships:** `ValueError`.

### `get_settings`

```python
def get_settings() -> Settings
```

**Source:** [app/core/config.py:57](../app/core/config.py#L57)

Get settings; behavior is defined by the linked implementation.

**Decorators:** `lru_cache`.

**Imported dependencies referenced:** `functools.lru_cache`

**Other calls / relationships:** `Settings`.

### Class `UISettings`

`class UISettings(BaseSettings)` — [app/core/config.py:61](../app/core/config.py#L61)

Uisettings; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
api_base_url: str = 'http://127.0.0.1:8000'
ui_timezone: str = 'Asia/Kolkata'
```

### `get_ui_settings`

```python
def get_ui_settings() -> UISettings
```

**Source:** [app/core/config.py:69](../app/core/config.py#L69)

Get ui settings; behavior is defined by the linked implementation.

**Decorators:** `lru_cache`.

**Imported dependencies referenced:** `functools.lru_cache`

**Other calls / relationships:** `UISettings`.

## Module `logging.py`

**Source:** [app/core/logging.py:1](../app/core/logging.py#L1)

**Internal dependencies:** None.

**External / standard-library dependencies:** `logging`, `structlog`

### `configure_logging`

```python
def configure_logging(level: str) -> None
```

**Source:** [app/core/logging.py:8](../app/core/logging.py#L8)

JSON logs on stdout, ready for Datadog ingestion.

**Imported dependencies referenced:** `logging`, `structlog`

## Module `observability.py`

**Source:** [app/core/observability.py:1](../app/core/observability.py#L1)

**Internal dependencies:** None.

**External / standard-library dependencies:** `collections.deque`, `langchain_core.callbacks.AsyncCallbackHandler`, `langchain_core.messages.AIMessage`, `langchain_core.outputs.LLMResult`, `math.ceil`, `structlog`, `typing.Any`

**Module state / exports:** `retrieval_latencies`.

### `latency_summary`

```python
def latency_summary() -> dict[str, int | float]
```

**Source:** [app/core/observability.py:15](../app/core/observability.py#L15)

Latency summary; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `math.ceil`

**Other calls / relationships:** `len`, `max`, `sorted`.

### Class `TokenUsageLogger`

`class TokenUsageLogger(AsyncCallbackHandler)` — [app/core/observability.py:23](../app/core/observability.py#L23)

Tokenusagelogger; behavior is defined by the linked implementation.

### `TokenUsageLogger.on_llm_end`

```python
async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None
```

**Source:** [app/core/observability.py:24](../app/core/observability.py#L24)

On llm end; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `langchain_core.messages.AIMessage`, `langchain_core.outputs.LLMResult`, `structlog`, `typing.Any`

**Other calls / relationships:** `getattr`, `isinstance`.

## Module `telemetry.py`

**Source:** [app/core/telemetry.py:1](../app/core/telemetry.py#L1)

**Internal dependencies:** None.

**External / standard-library dependencies:** `ddtrace.patch_all`

### `init_telemetry`

```python
def init_telemetry(enabled: bool) -> None
```

**Source:** [app/core/telemetry.py:4](../app/core/telemetry.py#L4)

Patch supported integrations for CLI startup.

Serve FastAPI with ddtrace-run so instrumentation starts before app creation.
Load .env into the process first; the SDK reads its own DD_* configuration.

**Imported dependencies referenced:** `ddtrace.patch_all`
