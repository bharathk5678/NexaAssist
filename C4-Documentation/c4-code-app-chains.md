# C4 code inventory: app/chains

**Language:** Python 3.14. **Scope:** direct modules listed below, with child inventories linked separately.

Pure LangChain ingestion, retrieval, reranking and answer-generation components. Named Runnable stages provide chain-level trace structure. No FastAPI or Streamlit imports.

**Location:** [app/chains](../app/chains)

## Observability and evaluation relevance

Runnable names include retrieve_policy, answer_policy and ingestion stages. assemble_context packs complete source units within the evidence budget. Retrieval logs stage timing; answer code validates citation identity and quoted substrings, not semantic truth.

## Child directories

- [app/chains/prompts](c4-code-app-chains-prompts.md)

## Module `__init__.py`

**Source:** [app/chains/__init__.py](../app/chains/__init__.py)

**Internal dependencies:** None.

**External / standard-library dependencies:** None.

No top-level functions or classes; module provides the exports above or a package marker.

## Module `answer.py`

**Source:** [app/chains/answer.py:1](../app/chains/answer.py#L1)

**Internal dependencies:** `app.chains.context.assemble_context`, `app.chains.context.render_context`, `app.chains.prompts.answer.ANSWER_PROMPT`, `app.core.config.Settings`, `app.models.answer.AnswerCitation`, `app.models.answer.AnswerDraft`, `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`

**External / standard-library dependencies:** `langchain_core.language_models.chat_models.BaseChatModel`, `langchain_core.runnables.Runnable`, `langchain_core.runnables.RunnableLambda`, `re`, `structlog`, `time.perf_counter`

**Module state / exports:** `logger`, `INSUFFICIENT_EVIDENCE`.

### `build_answer_chain`

```python
def build_answer_chain(retriever: Runnable[RetrieveRequest, RetrieveResponse], llm: BaseChatModel, settings: Settings) -> Runnable[RetrieveRequest, AnswerResponse]
```

**Source:** [app/chains/answer.py:20](../app/chains/answer.py#L20)

Retrieve evidence, generate a draft, and validate its citation references.

**Imported dependencies referenced:** `app.chains.context.assemble_context`, `app.chains.context.render_context`, `app.chains.prompts.answer.ANSWER_PROMPT`, `app.core.config.Settings`, `app.models.answer.AnswerCitation`, `app.models.answer.AnswerDraft`, `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `langchain_core.language_models.chat_models.BaseChatModel`, `langchain_core.runnables.Runnable`, `langchain_core.runnables.RunnableLambda`, `re`, `time.perf_counter`

**Other calls / relationships:** `RunnableLambda(answer).with_config`, `any`, `generation.ainvoke`, `int`, `item.model_dump`, `item.quote.strip`, `llm.with_structured_output`, `logger.warning`, `request.as_of.isoformat`, `retriever.ainvoke`, `round`.

### `build_answer_chain.answer`

```python
async def answer(request: RetrieveRequest) -> AnswerResponse
```

**Source:** [app/chains/answer.py:30](../app/chains/answer.py#L30)

Answer; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.chains.context.assemble_context`, `app.chains.context.render_context`, `app.models.answer.AnswerCitation`, `app.models.answer.AnswerDraft`, `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveRequest`, `re`, `time.perf_counter`

**Other calls / relationships:** `any`, `generation.ainvoke`, `int`, `item.model_dump`, `item.quote.strip`, `logger.warning`, `request.as_of.isoformat`, `retriever.ainvoke`, `round`.

## Module `chunking.py`

**Source:** [app/chains/chunking.py:1](../app/chains/chunking.py#L1)

**Internal dependencies:** None.

**External / standard-library dependencies:** `dataclasses.dataclass`, `dataclasses.field`, `langchain_text_splitters.RecursiveCharacterTextSplitter`, `re`, `unstructured.documents.elements.Element`, `unstructured.documents.elements.NarrativeText`, `unstructured.documents.elements.Table`, `unstructured.documents.elements.Title`

**Module state / exports:** `SECTION_TITLE`, `CLAUSE`.

### Class `Chunk`

`class Chunk()` — [app/chains/chunking.py:14](../app/chains/chunking.py#L14)

One citable child chunk: a numbered clause (or a piece of one) plus where it sits.

Declared fields (inherited fields remain on the linked base class):

```python
text: str
section_number: int
section: str
clause: str | None
clause_heading: str | None
has_table: bool
```

### Class `_Clause`

`class _Clause()` — [app/chains/chunking.py:26](../app/chains/chunking.py#L26)

Clause; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
section_number: int
section: str
clause: str | None
clause_heading: str | None
parts: list[tuple[str, bool]] = field(default_factory=list)
```

### `chunk_by_clause`

```python
def chunk_by_clause(elements: list[Element], max_characters: int, overlap: int) -> list[Chunk]
```

**Source:** [app/chains/chunking.py:34](../app/chains/chunking.py#L34)

Hybrid chunking: structure rules first, size rules second.

Structure: one chunk per numbered clause ("6.2 Processing fee. ..."). A table or
continuation line stays with the clause that introduces it, and a table is never split.
Size: only a clause longer than `max_characters` is split. Its tables become their own
chunks and its narrative is split at sentence boundaries with `overlap` characters
repeated. Text before section 1 is section 0, "Front matter".

**Imported dependencies referenced:** `langchain_text_splitters.RecursiveCharacterTextSplitter`, `unstructured.documents.elements.Element`, `unstructured.documents.elements.NarrativeText`, `unstructured.documents.elements.Table`, `unstructured.documents.elements.Title`

**Other calls / relationships:** `'\n'.join`, `CLAUSE.match`, `Chunk`, `SECTION_TITLE.match`, `_Clause`, `any`, `chunks.extend`, `clause.group`, `clauses.append`, `clauses[-1].parts.append`, `int`, `isinstance`, `len`, `pieces.append`, `pieces.extend`, `run.append`, `splitter.split_text`, `sum`, `title.group`.

## Module `context.py`

**Source:** [app/chains/context.py:1](../app/chains/context.py#L1)

**Internal dependencies:** `app.models.retrieval.RetrieveHit`

**External / standard-library dependencies:** `functools.lru_cache`, `json`, `tiktoken`

### `token_encoder`

```python
def token_encoder(name: str) -> tiktoken.Encoding
```

**Source:** [app/chains/context.py:13](../app/chains/context.py#L13)

Token encoder; behavior is defined by the linked implementation.

**Decorators:** `lru_cache`.

**Imported dependencies referenced:** `functools.lru_cache`, `tiktoken`

### `render_context`

```python
def render_context(sources: dict[int, RetrieveHit]) -> str
```

**Source:** [app/chains/context.py:17](../app/chains/context.py#L17)

Render context; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.models.retrieval.RetrieveHit`, `json`

**Other calls / relationships:** `hit.citation.model_dump`, `sources.items`.

### `assemble_context`

```python
def assemble_context(hits: list[RetrieveHit], max_tokens: int, encoding: str) -> dict[int, RetrieveHit]
```

**Source:** [app/chains/context.py:32](../app/chains/context.py#L32)

Pack complete parents, falling back to complete children; never cut a table.

The budget covers the serialized evidence payload, excluding prompt and output.
Reorder selected evidence so the two best-ranked passages sit at the edges.

**Decorators:** None.

**Imported dependencies referenced:** `app.models.retrieval.RetrieveHit`

**Other calls / relationships:** `dict`, `encoder.encode`, `hit.model_copy`, `len`, `list`, `render_context`, `seen.add`, `set`, `sources.items`, `token_encoder`.

## Module `embeddings.py`

**Source:** [app/chains/embeddings.py:1](../app/chains/embeddings.py#L1)

**Internal dependencies:** `app.core.config.Settings`

**External / standard-library dependencies:** `langchain_openai.OpenAIEmbeddings`

### `get_embeddings`

```python
def get_embeddings(settings: Settings) -> OpenAIEmbeddings
```

**Source:** [app/chains/embeddings.py:8](../app/chains/embeddings.py#L8)

Ingestion and retrieval must share this model and dimension.

**Imported dependencies referenced:** `app.core.config.Settings`, `langchain_openai.OpenAIEmbeddings`

## Module `ingestion.py`

**Source:** [app/chains/ingestion.py:1](../app/chains/ingestion.py#L1)

**Internal dependencies:** `app.chains.chunking.Chunk`, `app.chains.chunking.chunk_by_clause`, `app.chains.parsing.parse_document`, `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `app.models.ingestion.IngestResponse`

**External / standard-library dependencies:** `collections.Counter`, `collections.defaultdict`, `hashlib`, `json`, `langchain_core.documents.Document`, `langchain_core.runnables.Runnable`, `langchain_core.runnables.RunnableLambda`, `langchain_core.runnables.RunnablePassthrough`, `langchain_core.stores.BaseStore`, `langchain_core.vectorstores.VectorStore`, `typing.Any`, `unstructured.documents.elements.Element`

### `parent_key_prefix`

```python
def parent_key_prefix(doc_id: str) -> str
```

**Source:** [app/chains/ingestion.py:20](../app/chains/ingestion.py#L20)

Parent key prefix; behavior is defined by the linked implementation.

**Imported dependencies referenced:** None directly.

### `chunk_checksum`

```python
def chunk_checksum(text: str, metadata: dict[str, Any]) -> str
```

**Source:** [app/chains/ingestion.py:24](../app/chains/ingestion.py#L24)

Fingerprint text, metadata, embedding model and embedding dimensions.

Enrichment includes both embedding settings, so either change invalidates chunks.

**Imported dependencies referenced:** `hashlib`, `json`, `typing.Any`

**Other calls / relationships:** `payload.encode`.

### `build_ingestion_chain`

```python
def build_ingestion_chain(vector_store: VectorStore, parent_store: BaseStore[str, Document], settings: Settings) -> Runnable[dict[str, Any], IngestResponse]
```

**Source:** [app/chains/ingestion.py:52](../app/chains/ingestion.py#L52)

Write path: parse -> chunk -> enrich + hash -> compare -> embed + upsert.

Children are clause chunks (embedded, searched). Parents are whole sections, kept in
`parent_store` under `parent_id` so the read path can return the section around a match.
Only children whose checksum differs from the stored one are embedded.
Requests must match the configured corpus. Stored chunks with colliding IDs and
all existing exact-document parents must retain matching document and corpus
metadata; conflicting or missing identity/scope stops ingestion before writes.
Input: {"request": IngestRequest}. Run with `ainvoke`.

**Imported dependencies referenced:** `app.chains.chunking.Chunk`, `app.chains.chunking.chunk_by_clause`, `app.chains.parsing.parse_document`, `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `app.models.ingestion.IngestResponse`, `collections.Counter`, `collections.defaultdict`, `langchain_core.documents.Document`, `langchain_core.runnables.Runnable`, `langchain_core.runnables.RunnableLambda`, `langchain_core.runnables.RunnablePassthrough`, `langchain_core.stores.BaseStore`, `langchain_core.vectorstores.VectorStore`, `typing.Any`, `unstructured.documents.elements.Element`

**Other calls / relationships:** `'\n'.join`, `RunnableLambda(chunk).with_config`, `RunnableLambda(compare).with_config`, `RunnableLambda(embed_and_upsert).with_config`, `RunnableLambda(enrich).with_config`, `RunnableLambda(parse).with_config`, `ValueError`, `by_section.items`, `by_section[parent_id].append`, `children.append`, `chunk_checksum`, `document.metadata.get`, `header`, `len`, `parent_key_prefix`, `parent_store.amdelete`, `parent_store.amset`, `parent_store.ayield_keys`, `request.model_dump`, `stored.get`, `str`, `vector_store.aadd_documents`, `vector_store.aget_by_ids`.

### `build_ingestion_chain.parse`

```python
def parse(state: dict[str, Any]) -> list[Element]
```

**Source:** [app/chains/ingestion.py:46](../app/chains/ingestion.py#L46)

Parse; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.chains.parsing.parse_document`, `typing.Any`, `unstructured.documents.elements.Element`

### `build_ingestion_chain.chunk`

```python
def chunk(state: dict[str, Any]) -> list[Chunk]
```

**Source:** [app/chains/ingestion.py:49](../app/chains/ingestion.py#L49)

Chunk; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.chains.chunking.Chunk`, `app.chains.chunking.chunk_by_clause`, `typing.Any`

**Other calls / relationships:** `ValueError`.

### `build_ingestion_chain.enrich`

```python
def enrich(state: dict[str, Any]) -> dict[str, list[Document]]
```

**Source:** [app/chains/ingestion.py:59](../app/chains/ingestion.py#L59)

Enrich; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.chains.chunking.Chunk`, `app.models.ingestion.IngestRequest`, `collections.Counter`, `collections.defaultdict`, `langchain_core.documents.Document`, `typing.Any`

**Other calls / relationships:** `'\n'.join`, `by_section.items`, `by_section[parent_id].append`, `children.append`, `chunk_checksum`, `header`, `parent_key_prefix`, `request.model_dump`, `str`.

### `build_ingestion_chain.enrich.header`

```python
def header(section: str) -> str
```

**Source:** [app/chains/ingestion.py:63](../app/chains/ingestion.py#L63)

Header; behavior is defined by the linked implementation.

**Imported dependencies referenced:** None directly.

### `build_ingestion_chain.compare`

```python
async def compare(state: dict[str, Any]) -> list[Document]
```

**Source:** [app/chains/ingestion.py:176](../app/chains/ingestion.py#L176)

Check stored chunk and parent identity/scope, then select changed checksums.

**Imported dependencies referenced:** `langchain_core.documents.Document`, `typing.Any`

**Other calls / relationships:** `document.metadata.get`, `stored.get`, `vector_store.aget_by_ids`.

### `build_ingestion_chain.embed_and_upsert`

```python
async def embed_and_upsert(state: dict[str, Any]) -> IngestResponse
```

**Source:** [app/chains/ingestion.py:113](../app/chains/ingestion.py#L113)

Embed and upsert; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.models.ingestion.IngestRequest`, `app.models.ingestion.IngestResponse`, `langchain_core.documents.Document`, `typing.Any`

**Other calls / relationships:** `len`, `parent_key_prefix`, `parent_store.amdelete`, `parent_store.amset`, `parent_store.ayield_keys`, `vector_store.aadd_documents`.

## Module `llm.py`

**Source:** [app/chains/llm.py:1](../app/chains/llm.py#L1)

**Internal dependencies:** `app.core.config.Settings`, `app.core.observability.TokenUsageLogger`

**External / standard-library dependencies:** `langchain_openai.ChatOpenAI`

### `get_chat_model`

```python
def get_chat_model(settings: Settings) -> ChatOpenAI
```

**Source:** [app/chains/llm.py:9](../app/chains/llm.py#L9)

Get chat model; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.core.observability.TokenUsageLogger`, `langchain_openai.ChatOpenAI`

## Module `parsing.py`

**Source:** [app/chains/parsing.py:1](../app/chains/parsing.py#L1)

**Internal dependencies:** None.

**External / standard-library dependencies:** `collections.Counter`, `html.escape`, `pdfplumber`, `unstructured.documents.elements.Element`, `unstructured.documents.elements.ElementMetadata`, `unstructured.documents.elements.NarrativeText`, `unstructured.documents.elements.Table`, `unstructured.documents.elements.Title`, `unstructured.partition.auto.partition`

**Module state / exports:** `PAGE_MARGIN_PT`.

### `parse_document`

```python
def parse_document(path: str) -> list[Element]
```

**Source:** [app/chains/parsing.py:14](../app/chains/parsing.py#L14)

Parse a source document into ordered headings, paragraphs and whole tables.

**Imported dependencies referenced:** `unstructured.documents.elements.Element`, `unstructured.partition.auto.partition`

**Other calls / relationships:** `_parse_pdf`, `path.lower`, `path.lower().endswith`.

### `_parse_pdf`

```python
def _parse_pdf(path: str) -> list[Element]
```

**Source:** [app/chains/parsing.py:21](../app/chains/parsing.py#L21)

Born-digital PDFs only: tables come from ruling lines, headings from font size.

**Imported dependencies referenced:** `collections.Counter`, `pdfplumber`, `unstructured.documents.elements.Element`, `unstructured.documents.elements.NarrativeText`, `unstructured.documents.elements.Title`

**Other calls / relationships:** `' '.join`, `_table_element`, `blocks.append`, `content.find_tables`, `page.crop`, `paragraph.append`, `round`, `sizes.most_common`, `sorted`, `table.extract`, `text_area.extract_text_lines`, `text_area.outside_bbox`.

### `_table_element`

```python
def _table_element(rows: list[list[str | None]]) -> Table
```

**Source:** [app/chains/parsing.py:58](../app/chains/parsing.py#L58)

Table element; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `html.escape`, `unstructured.documents.elements.ElementMetadata`, `unstructured.documents.elements.Table`

**Other calls / relationships:** `' '.join`, `''.join`, `(cell or '').split`.

## Module `rerank.py`

**Source:** [app/chains/rerank.py:1](../app/chains/rerank.py#L1)

**Internal dependencies:** `app.chains.context.token_encoder`, `app.chains.prompts.rerank.rerank_prompt`, `app.core.config.Settings`

**External / standard-library dependencies:** `httpx`, `langchain_core.documents.Document`, `langchain_core.runnables.Runnable`, `langchain_core.runnables.RunnableLambda`, `math.exp`, `math.isfinite`, `pydantic.TypeAdapter`, `typing.Any`

### `relevance_probability`

```python
def relevance_probability(logprobs: dict[str, float]) -> float
```

**Source:** [app/chains/rerank.py:16](../app/chains/rerank.py#L16)

Normalize Qwen's exact lowercase yes/no tokens, without merging variants.

**Imported dependencies referenced:** `math.exp`, `math.isfinite`

**Other calls / relationships:** `ValueError`, `all`, `max`.

### `completion_probabilities`

```python
def completion_probabilities(payload: dict[str, Any]) -> dict[str, float]
```

**Source:** [app/chains/rerank.py:25](../app/chains/rerank.py#L25)

Accept native Ollama, legacy OpenAI, and content-array logprob shapes.

**Imported dependencies referenced:** `pydantic.TypeAdapter`, `typing.Any`

**Other calls / relationships:** `TypeAdapter(dict[str, float]).validate_python`, `ValueError`, `probabilities.get`.

### `build_rerank_chain`

```python
def build_rerank_chain(settings: Settings, *, transport: httpx.AsyncBaseTransport | None=None) -> Runnable[dict[str, Any], list[tuple[Document, float]]]
```

**Source:** [app/chains/rerank.py:46](../app/chains/rerank.py#L46)

Qwen3 pair scoring through native Ollama or OpenAI-compatible completions.

The installed Ollama model determines its execution engine. This adapter
does not convert GGUF weights to MLX or verify an MLX backend.

**Imported dependencies referenced:** `app.chains.context.token_encoder`, `app.chains.prompts.rerank.rerank_prompt`, `app.core.config.Settings`, `httpx`, `langchain_core.documents.Document`, `langchain_core.runnables.Runnable`, `langchain_core.runnables.RunnableLambda`, `typing.Any`

**Other calls / relationships:** `RunnableLambda(rerank).with_config`, `ValueError`, `client.post`, `completion_probabilities`, `len`, `relevance_probability`, `response.json`, `response.raise_for_status`, `scored.append`, `settings.rerank_api_key.get_secret_value`, `sorted`, `token_encoder(settings.token_encoding).encode`.

### `build_rerank_chain.rerank`

```python
async def rerank(value: dict[str, Any]) -> list[tuple[Document, float]]
```

**Source:** [app/chains/rerank.py:55](../app/chains/rerank.py#L55)

Rerank; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.chains.context.token_encoder`, `app.chains.prompts.rerank.rerank_prompt`, `httpx`, `langchain_core.documents.Document`, `typing.Any`

**Other calls / relationships:** `ValueError`, `client.post`, `completion_probabilities`, `len`, `relevance_probability`, `response.json`, `response.raise_for_status`, `scored.append`, `settings.rerank_api_key.get_secret_value`, `sorted`, `token_encoder(settings.token_encoding).encode`.

## Module `retrieval.py`

**Source:** [app/chains/retrieval.py:1](../app/chains/retrieval.py#L1)

**Internal dependencies:** `app.core.config.Settings`, `app.models.retrieval.Citation`, `app.models.retrieval.RetrieveHit`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.models.retrieval.RetrieveTimings`

**External / standard-library dependencies:** `langchain_core.documents.Document`, `langchain_core.runnables.Runnable`, `langchain_core.runnables.RunnableLambda`, `langchain_core.stores.BaseStore`, `langchain_core.vectorstores.VectorStore`, `structlog`, `time.perf_counter`, `typing.Any`

**Module state / exports:** `logger`.

### `build_retrieval_chain`

```python
def build_retrieval_chain(vector_store: VectorStore, parent_store: BaseStore[str, Document], settings: Settings, *, candidate_search: Runnable[dict[str, Any], list[tuple[Document, float]]] | None=None, reranker: Runnable[dict[str, Any], list[tuple[Document, float]]] | None=None) -> Runnable[RetrieveRequest, RetrieveResponse]
```

**Source:** [app/chains/retrieval.py:24](../app/chains/retrieval.py#L24)

Search indexed policy chunks, then expand each hit to its parent section.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.retrieval.Citation`, `app.models.retrieval.RetrieveHit`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.models.retrieval.RetrieveTimings`, `langchain_core.documents.Document`, `langchain_core.runnables.Runnable`, `langchain_core.runnables.RunnableLambda`, `langchain_core.stores.BaseStore`, `langchain_core.vectorstores.VectorStore`, `time.perf_counter`, `typing.Any`

**Other calls / relationships:** `RunnableLambda(retrieve).with_config`, `candidate_search.ainvoke`, `dict`, `enumerate`, `filters.append`, `hits.append`, `len`, `list`, `logger.info`, `logger.warning`, `max`, `parent_store.amget`, `request.as_of.isoformat`, `reranker.ainvoke`, `round`, `vector_store.asimilarity_search_with_score`, `zip`.

### `build_retrieval_chain.retrieve`

```python
async def retrieve(request: RetrieveRequest) -> RetrieveResponse
```

**Source:** [app/chains/retrieval.py:34](../app/chains/retrieval.py#L34)

Retrieve; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.models.retrieval.Citation`, `app.models.retrieval.RetrieveHit`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.models.retrieval.RetrieveTimings`, `time.perf_counter`

**Other calls / relationships:** `candidate_search.ainvoke`, `dict`, `enumerate`, `filters.append`, `hits.append`, `len`, `list`, `logger.info`, `logger.warning`, `max`, `parent_store.amget`, `request.as_of.isoformat`, `reranker.ainvoke`, `round`, `vector_store.asimilarity_search_with_score`, `zip`.
