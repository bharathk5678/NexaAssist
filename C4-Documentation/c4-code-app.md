# C4 code inventory: app

**Language:** Python 3.14. **Scope:** direct modules listed below, with child inventories linked separately.

Application entry points that compose the FastAPI process and delegate Streamlit startup. No independent LangChain or telemetry process is defined here.

**Location:** [app](../app)

## Observability and evaluation relevance

FastAPI instrumentation must start before application construction via ddtrace-run. Lifespan also calls init_telemetry and configures JSON logging.

## Child directories

- [app/api](c4-code-app-api.md)
- [app/chains](c4-code-app-chains.md)
- [app/core](c4-code-app-core.md)
- [app/database](c4-code-app-database.md)
- [app/evaluation](c4-code-app-evaluation.md)
- [app/models](c4-code-app-models.md)
- [app/services](c4-code-app-services.md)
- [app/ui](c4-code-app-ui.md)

## Module `__init__.py`

**Source:** [app/__init__.py](../app/__init__.py)

**Internal dependencies:** None.

**External / standard-library dependencies:** None.

No top-level functions or classes; module provides the exports above or a package marker.

## Module `main.py`

**Source:** [app/main.py:1](../app/main.py#L1)

**Internal dependencies:** `app.api.answer.router`, `app.api.feedback.router`, `app.api.operations.router`, `app.api.retrieval.router`, `app.chains.context.token_encoder`, `app.core.config.get_settings`, `app.core.logging.configure_logging`, `app.core.telemetry.init_telemetry`

**External / standard-library dependencies:** `asyncio`, `collections.abc.AsyncIterator`, `contextlib.asynccontextmanager`, `fastapi.FastAPI`

**Module state / exports:** `app`.

### `lifespan`

```python
async def lifespan(_app: FastAPI) -> AsyncIterator[None]
```

**Source:** [app/main.py:20](../app/main.py#L20)

Lifespan; behavior is defined by the linked implementation.

**Decorators:** `asynccontextmanager`.

**Imported dependencies referenced:** `app.chains.context.token_encoder`, `app.core.config.get_settings`, `app.core.logging.configure_logging`, `app.core.telemetry.init_telemetry`, `asyncio`, `collections.abc.AsyncIterator`, `contextlib.asynccontextmanager`, `fastapi.FastAPI`

### `create_app`

```python
def create_app() -> FastAPI
```

**Source:** [app/main.py:28](../app/main.py#L28)

Create app; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.api.answer.router`, `app.api.feedback.router`, `app.api.operations.router`, `app.api.retrieval.router`, `fastapi.FastAPI`

**Other calls / relationships:** `app.include_router`.

## Module `streamlit_app.py`

**Source:** [app/streamlit_app.py:1](../app/streamlit_app.py#L1)

**Internal dependencies:** `app.ui.app.main`

**External / standard-library dependencies:** None.

No top-level functions or classes; module provides the exports above or a package marker.
