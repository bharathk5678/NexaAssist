# C4 code inventory: app/ui

**Language:** Python 3.14. **Scope:** direct modules listed below, with child inventories linked separately.

Streamlit chat and review interface. Uses cached HTTPX client to call the API; chat history remains UI-session state and is not passed as model conversation context.

**Location:** [app/ui](../app/ui)

## Observability and evaluation relevance

No browser RUM setup is present. No trace ID is added to the response or shown in the chat UI. Backend observability depends on the API process and its startup environment.

## Module `__init__.py`

**Source:** [app/ui/__init__.py](../app/ui/__init__.py)

**Internal dependencies:** None.

**External / standard-library dependencies:** None.

No top-level functions or classes; module provides the exports above or a package marker.

## Module `app.py`

**Source:** [app/ui/app.py:1](../app/ui/app.py#L1)

**Internal dependencies:** `app.core.config.get_ui_settings`, `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`

**External / standard-library dependencies:** `datetime.datetime`, `httpx`, `pydantic.ValidationError`, `streamlit`, `typing.Any`, `uuid.uuid4`, `zoneinfo.ZoneInfo`

### `api_client`

```python
def api_client(base_url: str) -> httpx.Client
```

**Source:** [app/ui/app.py:18](../app/ui/app.py#L18)

Api client; behavior is defined by the linked implementation.

**Decorators:** `st.cache_resource`.

**Imported dependencies referenced:** `httpx`, `streamlit`

### `show_answer`

```python
def show_answer(result: AnswerResponse) -> None
```

**Source:** [app/ui/app.py:22](../app/ui/app.py#L22)

Show answer; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.models.answer.AnswerResponse`, `streamlit`

### `feedback_form`

```python
def feedback_form(client: httpx.Client, turn: dict[str, Any]) -> None
```

**Source:** [app/ui/app.py:34](../app/ui/app.py#L34)

Feedback form; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `httpx`, `streamlit`, `typing.Any`

**Other calls / relationships:** `client.post`, `response.raise_for_status`, `turn.get`.

### `review_feedback`

```python
def review_feedback(client: httpx.Client) -> None
```

**Source:** [app/ui/app.py:60](../app/ui/app.py#L60)

Review feedback; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `httpx`, `streamlit`

**Other calls / relationships:** `client.get`, `client.post`, `note.strip`, `record.update`, `response.json`, `response.raise_for_status`, `reviewer.strip`.

### `open_chat`

```python
def open_chat(identifier: str) -> None
```

**Source:** [app/ui/app.py:102](../app/ui/app.py#L102)

Open chat; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `streamlit`

### `send_question`

```python
def send_question(client: httpx.Client, turn: dict[str, Any]) -> None
```

**Source:** [app/ui/app.py:107](../app/ui/app.py#L107)

Call the existing API; chat history remains local to this UI session.

**Imported dependencies referenced:** `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveResponse`, `httpx`, `streamlit`, `typing.Any`

**Other calls / relationships:** `client.post`, `response.json`, `response.raise_for_status`, `schema.model_validate`, `schema.model_validate(response.json()).model_dump`, `turn.pop`.

### `show_turn`

```python
def show_turn(client: httpx.Client, turn: dict[str, Any]) -> bool
```

**Source:** [app/ui/app.py:125](../app/ui/app.py#L125)

Render one question and its evidence, returning whether to retry it.

**Imported dependencies referenced:** `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveResponse`, `httpx`, `streamlit`, `typing.Any`

**Other calls / relationships:** `feedback_form`, `len`, `show_answer`, `turn.get`.

### `main`

```python
def main() -> None
```

**Source:** [app/ui/app.py:162](../app/ui/app.py#L162)

Main; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.config.get_ui_settings`, `app.models.retrieval.RetrieveRequest`, `datetime.datetime`, `pydantic.ValidationError`, `streamlit`, `typing.Any`, `uuid.uuid4`, `zoneinfo.ZoneInfo`

**Other calls / relationships:** `api_client`, `conversations.get`, `conversations.items`, `list`, `product_id.strip`, `query.strip`, `request.model_dump`, `reversed`, `review_feedback`, `send_question`, `show_turn`, `turns.append`, `welcome.container`, `welcome.empty`.
