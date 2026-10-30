# C4 code inventory: app/database

**Language:** Python 3.14. **Scope:** direct modules listed below, with child inventories linked separately.

MongoDB client/store factories, feedback persistence, read-only diagnostics and hybrid Atlas retrieval adapter. Synchronous PyMongo helpers are called in worker threads where their service callers do so.

**Location:** [app/database](../app/database)

## Observability and evaluation relevance

pymongo.cmd can include hello/ismaster discovery calls unrelated to user queries. Database spans do not establish that a fastapi.request root was collected.

## Module `__init__.py`

**Source:** [app/database/__init__.py](../app/database/__init__.py)

**Internal dependencies:** None.

**External / standard-library dependencies:** None.

No top-level functions or classes; module provides the exports above or a package marker.

## Module `diagnostics.py`

**Source:** [app/database/diagnostics.py:1](../app/database/diagnostics.py#L1)

Read-only storage observations for the Session 5 teaching examples.

**Internal dependencies:** `app.core.config.Settings`, `app.database.mongo._database`

**External / standard-library dependencies:** `pymongo.timeout`, `typing.Any`

### `read_rag_snapshot`

```python
def read_rag_snapshot(settings: Settings) -> dict[str, Any]
```

**Source:** [app/database/diagnostics.py:13](../app/database/diagnostics.py#L13)

Read index definitions and chunk payloads, replacing vectors with their lengths.

The lesson caller runs this synchronous database work in a worker thread.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.database.mongo._database`, `pymongo.timeout`, `typing.Any`

**Other calls / relationships:** `_database(settings)[settings.mongodb_parent_collection].find`, `collection.aggregate`, `collection.list_search_indexes`, `list`, `row.get`.

## Module `feedback.py`

**Source:** [app/database/feedback.py:1](../app/database/feedback.py#L1)

**Internal dependencies:** `app.core.config.Settings`, `app.database.mongo._database`, `app.models.feedback.FeedbackRecord`, `app.models.feedback.FeedbackReview`

**External / standard-library dependencies:** `uuid.UUID`

### `save_feedback`

```python
def save_feedback(record: FeedbackRecord, settings: Settings) -> None
```

**Source:** [app/database/feedback.py:10](../app/database/feedback.py#L10)

Save feedback; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.database.mongo._database`, `app.models.feedback.FeedbackRecord`

**Other calls / relationships:** `_database(settings)[settings.mongodb_feedback_collection].insert_one`, `record.model_dump`, `str`.

### `list_feedback`

```python
def list_feedback(settings: Settings, limit: int) -> list[FeedbackRecord]
```

**Source:** [app/database/feedback.py:20](../app/database/feedback.py#L20)

List feedback; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.database.mongo._database`, `app.models.feedback.FeedbackRecord`

**Other calls / relationships:** `_database(settings)[settings.mongodb_feedback_collection].find`, `_database(settings)[settings.mongodb_feedback_collection].find({'institution': settings.institution}, {'_id': 0, 'institution': 0}).sort`, `_database(settings)[settings.mongodb_feedback_collection].find({'institution': settings.institution}, {'_id': 0, 'institution': 0}).sort('created_at', -1).limit`.

### `review_feedback`

```python
def review_feedback(feedback_id: UUID, review: FeedbackReview, settings: Settings) -> bool
```

**Source:** [app/database/feedback.py:30](../app/database/feedback.py#L30)

Review feedback; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.database.mongo._database`, `app.models.feedback.FeedbackReview`, `uuid.UUID`

**Other calls / relationships:** `_database(settings)[settings.mongodb_feedback_collection].update_one`, `review.model_dump`, `str`.

## Module `mongo.py`

**Source:** [app/database/mongo.py:1](../app/database/mongo.py#L1)

**Internal dependencies:** `app.core.config.Settings`

**External / standard-library dependencies:** `functools.lru_cache`, `langchain_core.embeddings.Embeddings`, `langchain_mongodb.MongoDBAtlasVectorSearch`, `langchain_mongodb.docstores.MongoDBDocStore`, `pymongo.MongoClient`, `pymongo.collection.Collection`, `pymongo.database.Database`, `typing.Any`

### `_client`

```python
def _client(uri: str) -> MongoClient[Any]
```

**Source:** [app/database/mongo.py:17](../app/database/mongo.py#L17)

Client; behavior is defined by the linked implementation.

**Decorators:** `lru_cache`.

**Imported dependencies referenced:** `functools.lru_cache`, `pymongo.MongoClient`, `typing.Any`

### `_database`

```python
def _database(settings: Settings) -> Database[Any]
```

**Source:** [app/database/mongo.py:21](../app/database/mongo.py#L21)

Database; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.config.Settings`, `pymongo.database.Database`, `typing.Any`

**Other calls / relationships:** `_client`, `settings.mongodb_uri.get_secret_value`.

### `get_vector_store`

```python
def get_vector_store(settings: Settings, embedding: Embeddings) -> MongoDBAtlasVectorSearch
```

**Source:** [app/database/mongo.py:25](../app/database/mongo.py#L25)

Chunk store shared by the write path and the read path.

The Atlas Vector Search index is created manually; see indexes.md.

**Imported dependencies referenced:** `app.core.config.Settings`, `langchain_core.embeddings.Embeddings`, `langchain_mongodb.MongoDBAtlasVectorSearch`

**Other calls / relationships:** `_database`.

### `get_parent_store`

```python
def get_parent_store(settings: Settings) -> MongoDBDocStore
```

**Source:** [app/database/mongo.py:41](../app/database/mongo.py#L41)

Whole sections keyed by parent_id, in their own collection. Not embedded.

**Imported dependencies referenced:** `app.core.config.Settings`, `langchain_mongodb.docstores.MongoDBDocStore`

**Other calls / relationships:** `_database`.

### `delete_stale_chunks`

```python
def delete_stale_chunks(collection: Collection[Any], doc_id: str, keep_ids: list[str], *, settings: Settings) -> int
```

**Source:** [app/database/mongo.py:101](../app/database/mongo.py#L101)

Retire obsolete chunks of `doc_id` only within the institution, jurisdiction and
confidentiality scope supplied by `settings`. Ingestion passes the same validated
configuration used by its chain. Stored IDs are unchanged.

**Imported dependencies referenced:** `pymongo.collection.Collection`, `typing.Any`

**Other calls / relationships:** `collection.delete_many`.

### `retire_document`

```python
def retire_document(settings: Settings, doc_id: str) -> dict[str, int]
```

**Source:** [app/database/mongo.py:52](../app/database/mongo.py#L52)

Explicitly retire one withdrawn document from both stores, scoped to this corpus.

**Imported dependencies referenced:** `app.core.config.Settings`

**Other calls / relationships:** `_database`, `database[settings.mongodb_collection].delete_many`, `database[settings.mongodb_parent_collection].delete_many`.

## Module `retrieval.py`

**Source:** [app/database/retrieval.py:1](../app/database/retrieval.py#L1)

**Internal dependencies:** `app.core.config.Settings`, `app.database.mongo._database`

**External / standard-library dependencies:** `langchain_core.documents.Document`, `langchain_core.runnables.Runnable`, `langchain_core.runnables.RunnableLambda`, `langchain_mongodb.MongoDBAtlasVectorSearch`, `langchain_mongodb.retrievers.MongoDBAtlasHybridSearchRetriever`, `typing.Any`

### `build_hybrid_search`

```python
def build_hybrid_search(vector_store: MongoDBAtlasVectorSearch, settings: Settings) -> Runnable[dict[str, Any], list[tuple[Document, float]]]
```

**Source:** [app/database/retrieval.py:14](../app/database/retrieval.py#L14)

Atlas BM25 + vector search fused by RRF, with no automatic index creation.

**Imported dependencies referenced:** `app.core.config.Settings`, `langchain_core.documents.Document`, `langchain_core.runnables.Runnable`, `langchain_core.runnables.RunnableLambda`, `langchain_mongodb.MongoDBAtlasVectorSearch`, `langchain_mongodb.retrievers.MongoDBAtlasHybridSearchRetriever`, `typing.Any`

**Other calls / relationships:** `RunnableLambda(search).with_config`, `float`, `retriever.ainvoke`.

### `build_hybrid_search.search`

```python
async def search(value: dict[str, Any]) -> list[tuple[Document, float]]
```

**Source:** [app/database/retrieval.py:19](../app/database/retrieval.py#L19)

Search; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `langchain_core.documents.Document`, `langchain_mongodb.retrievers.MongoDBAtlasHybridSearchRetriever`, `typing.Any`

**Other calls / relationships:** `float`, `retriever.ainvoke`.

### `resolve_reference_contexts`

```python
def resolve_reference_contexts(settings: Settings, references: list[dict[str, Any]]) -> list[str]
```

**Source:** [app/database/retrieval.py:33](../app/database/retrieval.py#L33)

Resolve golden source references to actual indexed text, in reference order.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.database.mongo._database`, `typing.Any`

**Other calls / relationships:** `'\n'.join`, `ValueError`, `collection.find`, `collection.find(query, {'text': 1}).sort`, `list`, `reference.get`, `texts.append`.
