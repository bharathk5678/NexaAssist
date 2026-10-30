# C4 code inventory: app/evaluation

**Language:** Python 3.14. **Scope:** direct modules listed below, with child inventories linked separately.

Offline RAG evaluation and teaching diagnostics. The main runner collects actual generation evidence, judges it, runs RAGAS and optionally joins scores to a Datadog LLM workflow.

**Location:** [app/evaluation](../app/evaluation)

## Observability and evaluation relevance

Online requests do not automatically run offline evaluations. LLMObs workflow, annotate, export_span, submit_evaluation and flush are used only when LLMObs.enabled; queued does not prove visibility in the signed-in UI.

## Data directory

[Teaching observation snapshots](c4-code-app-evaluation-datasets.md)

## Module `__init__.py`

**Source:** [app/evaluation/__init__.py:1](../app/evaluation/__init__.py#L1)

Offline diagnostics for the existing retrieval service.

**Internal dependencies:** None.

**External / standard-library dependencies:** None.

No top-level functions or classes; module provides the exports above or a package marker.

## Module `answer_evaluation.py`

**Source:** [app/evaluation/answer_evaluation.py:1](../app/evaluation/answer_evaluation.py#L1)

Evaluation contracts and mechanical checks; these do not score semantic truth.

**Internal dependencies:** `app.chains.answer.INSUFFICIENT_EVIDENCE`, `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveHit`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`

**External / standard-library dependencies:** `pathlib.Path`, `pydantic.BaseModel`, `pydantic.ConfigDict`, `pydantic.Field`, `re`, `typing.Literal`

### Class `ExpectedEvidence`

`class ExpectedEvidence(BaseModel)` — [app/evaluation/answer_evaluation.py:16](../app/evaluation/answer_evaluation.py#L16)

Expectedevidence; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
doc_id: str = Field(min_length=1)
clause: str | None = None
clause_key: str | None = None
```

### Class `GoldenAnswer`

`class GoldenAnswer(BaseModel)` — [app/evaluation/answer_evaluation.py:24](../app/evaluation/answer_evaluation.py#L24)

Goldenanswer; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
input: RetrieveRequest
expected_output: str = Field(min_length=1)
context: list[ExpectedEvidence]
expected_status: Literal['answered', 'insufficient_evidence']
```

### Class `EvidenceContext`

`class EvidenceContext(BaseModel)` — [app/evaluation/answer_evaluation.py:33](../app/evaluation/answer_evaluation.py#L33)

Evidencecontext; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
evidence_id: int = Field(ge=1)
hit: RetrieveHit
```

### Class `EvaluationRecord`

`class EvaluationRecord(BaseModel)` — [app/evaluation/answer_evaluation.py:40](../app/evaluation/answer_evaluation.py#L40)

Evaluationrecord; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
case_id: str
golden: GoldenAnswer
response: AnswerResponse
sources: list[EvidenceContext]
```

### `load_golden`

```python
def load_golden(path: Path) -> list[GoldenAnswer]
```

**Source:** [app/evaluation/answer_evaluation.py:56](../app/evaluation/answer_evaluation.py#L56)

Load golden; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `pathlib.Path`

**Other calls / relationships:** `GoldenAnswer.model_validate_json`, `ValueError`, `line.strip`, `path.read_text`, `path.read_text().splitlines`.

### `capture_sources`

```python
def capture_sources(retrieved: RetrieveResponse) -> list[EvidenceContext]
```

**Source:** [app/evaluation/answer_evaluation.py:67](../app/evaluation/answer_evaluation.py#L67)

Mirror the answer chain's document/version/parent deduplication, in order.

**Imported dependencies referenced:** `app.models.retrieval.RetrieveHit`, `app.models.retrieval.RetrieveResponse`

**Other calls / relationships:** `EvidenceContext`, `enumerate`, `unique.setdefault`, `unique.values`.

### `mechanical_checks`

```python
def mechanical_checks(record: EvaluationRecord) -> dict[str, bool | float | None]
```

**Source:** [app/evaluation/answer_evaluation.py:77](../app/evaluation/answer_evaluation.py#L77)

Citation identity/quote checks and child-ID coverage, never semantic recall.

**Imported dependencies referenced:** `app.chains.answer.INSUFFICIENT_EVIDENCE`, `re`

**Other calls / relationships:** `all`, `any`, `bool`, `citation.quote.strip`, `int`, `len`, `sum`.

## Module `check_reranker.py`

**Source:** [app/evaluation/check_reranker.py:1](../app/evaluation/check_reranker.py#L1)

**Internal dependencies:** `app.chains.rerank.build_rerank_chain`, `app.core.config.get_settings`, `app.core.logging.configure_logging`

**External / standard-library dependencies:** `argparse`, `asyncio`, `datetime.UTC`, `datetime.datetime`, `httpx`, `json`, `langchain_core.documents.Document`, `pathlib.Path`, `structlog`, `urllib.parse.urlparse`

### `check`

```python
async def check() -> dict[str, object]
```

**Source:** [app/evaluation/check_reranker.py:19](../app/evaluation/check_reranker.py#L19)

Check; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.chains.rerank.build_rerank_chain`, `app.core.config.get_settings`, `datetime.UTC`, `datetime.datetime`, `httpx`, `langchain_core.documents.Document`, `urllib.parse.urlparse`

**Other calls / relationships:** `ValueError`, `build_rerank_chain(settings).ainvoke`, `isinstance`, `str`, `type`.

### `main`

```python
def main() -> None
```

**Source:** [app/evaluation/check_reranker.py:53](../app/evaluation/check_reranker.py#L53)

Main; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.logging.configure_logging`, `argparse`, `asyncio`, `json`, `pathlib.Path`, `structlog`

**Other calls / relationships:** `SystemExit`, `args.output.parent.mkdir`, `args.output.write_text`, `check`, `parser.add_argument`, `parser.parse_args`.

## Module `failure_demo.py`

**Source:** [app/evaluation/failure_demo.py:1](../app/evaluation/failure_demo.py#L1)

Controlled fixtures using repository policy facts, never live Atlas observations.

**Internal dependencies:** `app.chains.answer.INSUFFICIENT_EVIDENCE`, `app.evaluation.answer_evaluation.EvaluationRecord`, `app.evaluation.answer_evaluation.capture_sources`, `app.evaluation.answer_evaluation.load_golden`, `app.evaluation.answer_evaluation.mechanical_checks`, `app.models.answer.AnswerCitation`, `app.models.answer.AnswerResponse`, `app.models.retrieval.Citation`, `app.models.retrieval.RetrieveHit`, `app.models.retrieval.RetrieveResponse`, `app.models.retrieval.RetrieveTimings`

**External / standard-library dependencies:** `pathlib.Path`

### `demo_report`

```python
def demo_report(dataset: Path) -> dict[str, object]
```

**Source:** [app/evaluation/failure_demo.py:18](../app/evaluation/failure_demo.py#L18)

Demo report; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.chains.answer.INSUFFICIENT_EVIDENCE`, `app.evaluation.answer_evaluation.EvaluationRecord`, `app.evaluation.answer_evaluation.capture_sources`, `app.evaluation.answer_evaluation.load_golden`, `app.evaluation.answer_evaluation.mechanical_checks`, `app.models.answer.AnswerCitation`, `app.models.answer.AnswerResponse`, `app.models.retrieval.Citation`, `app.models.retrieval.RetrieveHit`, `app.models.retrieval.RetrieveResponse`, `app.models.retrieval.RetrieveTimings`, `pathlib.Path`

**Other calls / relationships:** `base.model_copy`, `response.citations[0].model_copy`, `response.model_copy`.

## Module `rag_failure_examples.py`

**Source:** [app/evaluation/rag_failure_examples.py:1](../app/evaluation/rag_failure_examples.py#L1)

Read-only Atlas examples: python -m app.evaluation.rag_failure_examples R1.

Retrieval cases call Atlas and the configured embedding provider. Staleness and
compatibility fault injections change local snapshots only, never stored data.

**Internal dependencies:** `app.chains.embeddings.get_embeddings`, `app.chains.ingestion.build_ingestion_chain`, `app.chains.ingestion.chunk_checksum`, `app.chains.retrieval.build_retrieval_chain`, `app.core.config.Settings`, `app.core.config.get_settings`, `app.core.logging.configure_logging`, `app.database.diagnostics.read_rag_snapshot`, `app.database.mongo.get_parent_store`, `app.database.mongo.get_vector_store`, `app.evaluation.rag_failure_modes.ChunkSnapshot`, `app.evaluation.rag_failure_modes.EvidenceRef`, `app.evaluation.rag_failure_modes.diagnose_embeddings`, `app.evaluation.rag_failure_modes.diagnose_expanded_context`, `app.evaluation.rag_failure_modes.diagnose_parent_links`, `app.evaluation.rag_failure_modes.diagnose_retrieval`, `app.evaluation.rag_failure_modes.diagnose_staleness`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.services.ingestion.requests_from_register`

**External / standard-library dependencies:** `argparse`, `asyncio`, `collections.Counter`, `datetime.UTC`, `datetime.datetime`, `json`, `langchain_core.documents.Document`, `langchain_core.stores.InMemoryStore`, `langchain_core.vectorstores.VectorStore`, `openai.OpenAIError`, `pathlib.Path`, `pymongo.errors.PyMongoError`, `structlog`, `typing.Any`, `typing.cast`, `unittest.mock.AsyncMock`, `unittest.mock.Mock`

**Module state / exports:** `CASE_IDS`, `ROOT`, `FEE_QUERY`, `FOCUSED_QUERY`, `FEE_REFS`.

### `_source_manifests`

```python
async def _source_manifests(settings: Settings) -> tuple[list[ChunkSnapshot], list[ChunkSnapshot]]
```

**Source:** [app/evaluation/rag_failure_examples.py:57](../app/evaluation/rag_failure_examples.py#L57)

Run the actual parse/chunk/enrich path while capturing all writes in memory.

**Imported dependencies referenced:** `app.chains.ingestion.build_ingestion_chain`, `app.chains.ingestion.chunk_checksum`, `app.core.config.Settings`, `app.evaluation.rag_failure_modes.ChunkSnapshot`, `app.services.ingestion.requests_from_register`, `langchain_core.documents.Document`, `langchain_core.stores.InMemoryStore`, `langchain_core.vectorstores.VectorStore`, `typing.Any`, `typing.cast`, `unittest.mock.AsyncMock`, `unittest.mock.Mock`

**Other calls / relationships:** `chain.ainvoke`, `children.extend`, `parent_store.amget`, `parent_store.ayield_keys`, `zip`.

### `_source_manifests.capture`

```python
async def capture(documents: list[Document], **kwargs: Any) -> list[str]
```

**Source:** [app/evaluation/rag_failure_examples.py:61](../app/evaluation/rag_failure_examples.py#L61)

Capture; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `langchain_core.documents.Document`, `typing.Any`, `typing.cast`

**Other calls / relationships:** `children.extend`.

### `example_report`

```python
async def example_report(selected: str | None=None) -> dict[str, Any]
```

**Source:** [app/evaluation/rag_failure_examples.py:89](../app/evaluation/rag_failure_examples.py#L89)

Example report; behavior is defined by the linked implementation.

**Decorators:** None.

**Imported dependencies referenced:** `app.chains.embeddings.get_embeddings`, `app.chains.ingestion.chunk_checksum`, `app.chains.retrieval.build_retrieval_chain`, `app.core.config.get_settings`, `app.database.diagnostics.read_rag_snapshot`, `app.database.mongo.get_parent_store`, `app.database.mongo.get_vector_store`, `app.evaluation.rag_failure_modes.ChunkSnapshot`, `app.evaluation.rag_failure_modes.EvidenceRef`, `app.evaluation.rag_failure_modes.diagnose_embeddings`, `app.evaluation.rag_failure_modes.diagnose_expanded_context`, `app.evaluation.rag_failure_modes.diagnose_parent_links`, `app.evaluation.rag_failure_modes.diagnose_retrieval`, `app.evaluation.rag_failure_modes.diagnose_staleness`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `asyncio`, `collections.Counter`, `datetime.UTC`, `datetime.datetime`, `json`, `langchain_core.documents.Document`, `typing.Any`

**Other calls / relationships:** `(ROOT / 'evaluation/datasets/retrieval.jsonl').read_text`, `(ROOT / 'evaluation/datasets/retrieval.jsonl').read_text().splitlines`, `Counter((row['doc_id'] for row in chunks)).items`, `ValueError`, `_source_manifests`, `chain.ainvoke`, `cohort.append`, `dict`, `h.citation.model_dump`, `hit.model_copy`, `hits.append`, `inventory.items`, `len`, `local_parents.get`, `parents.items`, `parents[parent_id].model_copy`, `r.get`, `replay`, `request.model_dump`, `request.model_dump_json`, `response.model_copy`, `response.timings.model_dump`, `retrieve`, `row.get`, `row.items`, `s.chunk_id.startswith`, `selected.startswith`, `snapshots[0].model_copy`, `sorted`, `stale_parents.items`, `str`, `sum`, `wanted`.

### `example_report.retrieve`

```python
async def retrieve(query: str, refs: list[EvidenceRef], **changes: Any) -> dict[str, Any]
```

**Source:** [app/evaluation/rag_failure_examples.py:159](../app/evaluation/rag_failure_examples.py#L159)

Retrieve; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.evaluation.rag_failure_modes.EvidenceRef`, `app.evaluation.rag_failure_modes.diagnose_expanded_context`, `app.evaluation.rag_failure_modes.diagnose_retrieval`, `app.models.retrieval.RetrieveRequest`, `asyncio`, `typing.Any`

**Other calls / relationships:** `chain.ainvoke`, `h.citation.model_dump`, `len`, `request.model_dump`, `request.model_dump_json`, `response.timings.model_dump`.

### `example_report.replay`

```python
def replay(local_parents: dict[str, Document]) -> RetrieveResponse
```

**Source:** [app/evaluation/rag_failure_examples.py:283](../app/evaluation/rag_failure_examples.py#L283)

Replay; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.models.retrieval.RetrieveResponse`, `langchain_core.documents.Document`

**Other calls / relationships:** `hit.model_copy`, `hits.append`, `local_parents.get`, `response.model_copy`.

### `main`

```python
def main() -> None
```

**Source:** [app/evaluation/rag_failure_examples.py:405](../app/evaluation/rag_failure_examples.py#L405)

Main; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.logging.configure_logging`, `argparse`, `asyncio`, `openai.OpenAIError`, `pymongo.errors.PyMongoError`, `structlog`

**Other calls / relationships:** `SystemExit`, `example_report`, `parser.add_argument`, `parser.parse_args`, `type`.

## Module `rag_failure_modes.py`

**Source:** [app/evaluation/rag_failure_modes.py:1](../app/evaluation/rag_failure_modes.py#L1)

Run a controlled offline lesson: python -m app.evaluation.rag_failure_modes.

**Internal dependencies:** `app.chains.ingestion.chunk_checksum`, `app.core.config.Settings`, `app.core.logging.configure_logging`, `app.models.retrieval.RetrieveResponse`

**External / standard-library dependencies:** `collections.abc.Mapping`, `collections.abc.Sequence`, `langchain_core.documents.Document`, `pydantic.BaseModel`, `pydantic.ConfigDict`, `pydantic.Field`, `structlog`

### Class `EvidenceRef`

`class EvidenceRef(BaseModel)` — [app/evaluation/rag_failure_modes.py:17](../app/evaluation/rag_failure_modes.py#L17)

Evidenceref; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
doc_id: str = Field(min_length=1)
clause: str | None = None
```

### Class `ChunkSnapshot`

`class ChunkSnapshot(BaseModel)` — [app/evaluation/rag_failure_modes.py:24](../app/evaluation/rag_failure_modes.py#L24)

A source/index manifest entry; dimensions describe the stored vector.

Declared fields (inherited fields remain on the linked base class):

```python
chunk_id: str = Field(min_length=1)
checksum: str | None = Field(default=None, min_length=1)
embedding_model: str | None = Field(default=None, min_length=1)
embedding_dimensions: int | None = Field(default=None, ge=0)
```

### `diagnose_retrieval`

```python
def diagnose_retrieval(response: RetrieveResponse, expected: Sequence[EvidenceRef]) -> dict[str, object]
```

**Source:** [app/evaluation/rag_failure_modes.py:35](../app/evaluation/rag_failure_modes.py#L35)

Check expected citation coverage, including nonempty but incorrect results.

**Imported dependencies referenced:** `app.models.retrieval.RetrieveResponse`, `collections.abc.Sequence`

**Other calls / relationships:** `ValueError`, `any`, `len`, `reference.model_dump`.

### `_chunk_body`

```python
def _chunk_body(document: Document) -> str
```

**Source:** [app/evaluation/rag_failure_modes.py:58](../app/evaluation/rag_failure_modes.py#L58)

Chunk body; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `langchain_core.documents.Document`

**Other calls / relationships:** `document.page_content.partition`, `header.startswith`.

### `diagnose_expanded_context`

```python
def diagnose_expanded_context(response: RetrieveResponse, expected: Sequence[EvidenceRef], source_chunks: Sequence[Document]) -> dict[str, object]
```

**Source:** [app/evaluation/rag_failure_modes.py:63](../app/evaluation/rag_failure_modes.py#L63)

Check verbatim source-clause bodies in returned context, separately from citations.

This measures text availability, not semantic correctness or answer attribution.

**Imported dependencies referenced:** `app.models.retrieval.RetrieveResponse`, `collections.abc.Sequence`, `langchain_core.documents.Document`

**Other calls / relationships:** `(covered if present else missing).append`, `ValueError`, `_chunk_body`, `_chunk_body(chunk).strip`, `all`, `any`, `bool`, `chunk.metadata.get`, `reference.model_dump`, `unindexed.append`.

### `diagnose_parent_links`

```python
def diagnose_parent_links(chunks: Sequence[Document], parents: Mapping[str, Document]) -> dict[str, object]
```

**Source:** [app/evaluation/rag_failure_modes.py:106](../app/evaluation/rag_failure_modes.py#L106)

Check existence, policy scope and body containment across the two stores.

**Imported dependencies referenced:** `collections.abc.Mapping`, `collections.abc.Sequence`, `langchain_core.documents.Document`

**Other calls / relationships:** `_chunk_body`, `_chunk_body(chunk).strip`, `absent.append`, `any`, `chunk.metadata.get`, `mismatched.append`, `missing.append`, `parent.metadata.get`, `parents.get`, `referenced.add`, `set`, `sorted`.

### `_by_id`

```python
def _by_id(chunks: Sequence[ChunkSnapshot]) -> dict[str, ChunkSnapshot]
```

**Source:** [app/evaluation/rag_failure_modes.py:150](../app/evaluation/rag_failure_modes.py#L150)

By id; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `collections.abc.Sequence`

**Other calls / relationships:** `ValueError`, `len`.

### `diagnose_staleness`

```python
def diagnose_staleness(source: Sequence[ChunkSnapshot], indexed: Sequence[ChunkSnapshot]) -> dict[str, object]
```

**Source:** [app/evaluation/rag_failure_modes.py:157](../app/evaluation/rag_failure_modes.py#L157)

Compare a freshly prepared source manifest to a complete stored manifest.

This checks stored chunk freshness, not the Atlas Search index's readiness.

**Imported dependencies referenced:** `collections.abc.Sequence`

**Other calls / relationships:** `ValueError`, `_by_id`, `any`, `expected.keys`, `sorted`, `stored.keys`.

### `diagnose_embeddings`

```python
def diagnose_embeddings(indexed: Sequence[ChunkSnapshot], expected_model: str, expected_dimensions: int) -> dict[str, object]
```

**Source:** [app/evaluation/rag_failure_modes.py:183](../app/evaluation/rag_failure_modes.py#L183)

Check embedding compatibility; statistical distribution drift is not measured.

**Imported dependencies referenced:** `collections.abc.Sequence`

**Other calls / relationships:** `ValueError`, `_by_id`, `expected_model.strip`, `sorted`.

### `demo_report`

```python
def demo_report() -> dict[str, object]
```

**Source:** [app/evaluation/rag_failure_modes.py:203](../app/evaluation/rag_failure_modes.py#L203)

Synthetic snapshots and responses; no Atlas, embeddings, or model downloads.

**Imported dependencies referenced:** `app.chains.ingestion.chunk_checksum`, `app.core.config.Settings`, `app.models.retrieval.RetrieveResponse`

**Other calls / relationships:** `ChunkSnapshot`, `EvidenceRef`, `diagnose_embeddings`, `diagnose_retrieval`, `diagnose_staleness`, `int`, `response.model_copy`, `source[0].model_copy`, `source[1].model_copy`, `str`.

### `main`

```python
def main() -> None
```

**Source:** [app/evaluation/rag_failure_modes.py:276](../app/evaluation/rag_failure_modes.py#L276)

Main; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.logging.configure_logging`, `structlog`

**Other calls / relationships:** `demo_report`.

## Module `ragas_metrics.py`

**Source:** [app/evaluation/ragas_metrics.py:1](../app/evaluation/ragas_metrics.py#L1)

RAGAS collections API, using the existing LangChain provider configuration.

**Internal dependencies:** None. The unused alternate record-scoring method was removed; batch and live evaluation use the same metric adapters below.

**External / standard-library dependencies:** `langchain_core.embeddings.Embeddings`, `langchain_core.language_models.chat_models.BaseChatModel`, `pydantic.BaseModel`, `ragas.embeddings.base.BaseRagasEmbedding`, `ragas.llms.base.InstructorBaseRagasLLM`, `ragas.metrics.collections.AnswerRelevancy`, `ragas.metrics.collections.ContextPrecision`, `ragas.metrics.collections.ContextRecall`, `ragas.metrics.collections.Faithfulness`, `typing.Any`

### Class `StructuredJudge`

`class StructuredJudge(InstructorBaseRagasLLM)` — [app/evaluation/ragas_metrics.py:19](../app/evaluation/ragas_metrics.py#L19)

Keep RAGAS on the same Responses API path as answer generation.

### `StructuredJudge.__init__`

```python
def __init__(self, llm: BaseChatModel) -> None
```

**Source:** [app/evaluation/ragas_metrics.py:22](../app/evaluation/ragas_metrics.py#L22)

Init; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `langchain_core.language_models.chat_models.BaseChatModel`

### `StructuredJudge.generate`

```python
def generate[T: BaseModel](self, prompt: str, response_model: type[T]) -> T
```

**Source:** [app/evaluation/ragas_metrics.py:25](../app/evaluation/ragas_metrics.py#L25)

Generate; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `pydantic.BaseModel`

**Other calls / relationships:** `response_model.model_validate`, `self.llm.with_structured_output`, `self.llm.with_structured_output(response_model, method='json_schema', strict=True).invoke`.

### `StructuredJudge.agenerate`

```python
async def agenerate[T: BaseModel](self, prompt: str, response_model: type[T]) -> T
```

**Source:** [app/evaluation/ragas_metrics.py:31](../app/evaluation/ragas_metrics.py#L31)

Agenerate; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `pydantic.BaseModel`

**Other calls / relationships:** `response_model.model_validate`, `self.llm.with_structured_output`, `self.llm.with_structured_output(response_model, method='json_schema', strict=True).ainvoke`.

### Class `MetricEmbeddings`

`class MetricEmbeddings(BaseRagasEmbedding)` — [app/evaluation/ragas_metrics.py:38](../app/evaluation/ragas_metrics.py#L38)

Metricembeddings; behavior is defined by the linked implementation.

### `MetricEmbeddings.__init__`

```python
def __init__(self, embeddings: Embeddings) -> None
```

**Source:** [app/evaluation/ragas_metrics.py:39](../app/evaluation/ragas_metrics.py#L39)

Init; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `langchain_core.embeddings.Embeddings`

**Other calls / relationships:** `super`, `super().__init__`.

### `MetricEmbeddings.embed_text`

```python
def embed_text(self, text: str, **kwargs: Any) -> list[float]
```

**Source:** [app/evaluation/ragas_metrics.py:43](../app/evaluation/ragas_metrics.py#L43)

Embed text; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `typing.Any`

**Other calls / relationships:** `self.embeddings.embed_query`.

### `MetricEmbeddings.aembed_text`

```python
async def aembed_text(self, text: str, **kwargs: Any) -> list[float]
```

**Source:** [app/evaluation/ragas_metrics.py:46](../app/evaluation/ragas_metrics.py#L46)

Aembed text; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `typing.Any`

**Other calls / relationships:** `self.embeddings.aembed_query`.

### Class `RagasScorer`

`class RagasScorer()` — [app/evaluation/ragas_metrics.py:50](../app/evaluation/ragas_metrics.py#L50)

Ragasscorer; behavior is defined by the linked implementation.

### `RagasScorer.__init__`

```python
def __init__(self, llm: BaseChatModel, embeddings: Embeddings) -> None
```

**Source:** [app/evaluation/ragas_metrics.py:51](../app/evaluation/ragas_metrics.py#L51)

Init; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `langchain_core.embeddings.Embeddings`, `langchain_core.language_models.chat_models.BaseChatModel`, `ragas.metrics.collections.AnswerRelevancy`, `ragas.metrics.collections.ContextPrecision`, `ragas.metrics.collections.ContextRecall`, `ragas.metrics.collections.Faithfulness`

**Other calls / relationships:** `MetricEmbeddings`, `StructuredJudge`.

## Module `run.py`

**Source:** [app/evaluation/run.py:1](../app/evaluation/run.py#L1)

**Internal dependencies:** `app.chains.answer.build_answer_chain`, `app.chains.context.assemble_context`, `app.chains.llm.get_chat_model`, `app.chains.prompts.judge.JUDGE_PROMPT`, `app.chains.prompts.judge.JUDGE_VERSION`, `app.core.config.Settings`, `app.core.config.get_settings`, `app.core.logging.configure_logging`, `app.database.retrieval.resolve_reference_contexts`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.services.retrieval.retrieve_policy`

**External / standard-library dependencies:** `argparse`, `asyncio`, `contextlib.nullcontext`, `datetime.UTC`, `datetime.datetime`, `ddtrace.llmobs.LLMObs`, `importlib.metadata.version`, `json`, `langchain_core.runnables.RunnableLambda`, `langchain_core.tracers.run_collector.RunCollectorCallbackHandler`, `math.isfinite`, `openai.AsyncOpenAI`, `pathlib.Path`, `pydantic.BaseModel`, `pydantic.ConfigDict`, `pydantic.Field`, `ragas.embeddings.OpenAIEmbeddings`, `ragas.llms.llm_factory`, `ragas.metrics.collections.AnswerRelevancy`, `ragas.metrics.collections.ContextPrecision`, `ragas.metrics.collections.ContextRecall`, `ragas.metrics.collections.Faithfulness`, `structlog`, `typing.Any`, `typing.Literal`

**Module state / exports:** `ROOT`, `logger`.

### Class `GoldenCase`

`class GoldenCase(BaseModel)` — [app/evaluation/run.py:35](../app/evaluation/run.py#L35)

Goldencase; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
input: RetrieveRequest
expected_output: str
context: list[dict[str, Any]]
expected_status: Literal['answered', 'insufficient_evidence'] = 'answered'
```

### Class `JudgeScore`

`class JudgeScore(BaseModel)` — [app/evaluation/run.py:44](../app/evaluation/run.py#L44)

Judgescore; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
correctness: float = Field(ge=0, le=1, allow_inf_nan=False)
groundedness: float = Field(ge=0, le=1, allow_inf_nan=False)
rationale: str
```

### `load_cases`

```python
def load_cases(path: Path) -> list[GoldenCase]
```

**Source:** [app/evaluation/run.py:52](../app/evaluation/run.py#L52)

Load cases; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `pathlib.Path`

**Other calls / relationships:** `GoldenCase.model_validate_json`, `ValueError`, `line.strip`, `path.read_text`, `path.read_text().splitlines`.

### `trace_summary`

```python
def trace_summary(runs: list[Any]) -> list[dict[str, Any]]
```

**Source:** [app/evaluation/run.py:63](../app/evaluation/run.py#L63)

Trace summary; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `typing.Any`

**Other calls / relationships:** `(run.end_time - run.start_time).total_seconds`, `bool`, `round`, `spans.append`, `spans.extend`, `trace_summary`.

### `collect_records`

```python
async def collect_records(cases: list[GoldenCase], settings: Settings) -> list[dict[str, Any]]
```

**Source:** [app/evaluation/run.py:81](../app/evaluation/run.py#L81)

Generate once per case; evaluate the exact evidence passed to that generation.

**Decorators:** None.

**Imported dependencies referenced:** `app.chains.answer.build_answer_chain`, `app.chains.context.assemble_context`, `app.chains.llm.get_chat_model`, `app.chains.prompts.judge.JUDGE_PROMPT`, `app.chains.prompts.judge.JUDGE_VERSION`, `app.core.config.Settings`, `app.database.retrieval.resolve_reference_contexts`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.services.retrieval.retrieve_policy`, `asyncio`, `contextlib.nullcontext`, `ddtrace.llmobs.LLMObs`, `json`, `langchain_core.runnables.RunnableLambda`, `langchain_core.tracers.run_collector.RunCollectorCallbackHandler`, `typing.Any`

**Other calls / relationships:** `JudgeScore.model_validate`, `RunnableLambda(retrieve).with_config`, `RunnableLambda(retrieve).with_config(run_name='evaluation_retrieval').ainvoke`, `answer.model_dump`, `case.input.model_dump`, `chain.ainvoke`, `judge.ainvoke`, `model.with_structured_output`, `record.update`, `records.append`, `retrieved.timings.model_dump`, `score.model_dump`, `sources.values`, `trace_summary`.

### `collect_records.retrieve`

```python
async def retrieve(request: RetrieveRequest) -> RetrieveResponse
```

**Source:** [app/evaluation/run.py:97](../app/evaluation/run.py#L97)

Retrieve; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.services.retrieval.retrieve_policy`

### `collect_records.replay`

```python
def replay(_request: RetrieveRequest, evidence: RetrieveResponse=retrieved) -> RetrieveResponse
```

**Source:** [app/evaluation/run.py:109](../app/evaluation/run.py#L109)

Replay; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`

### `evaluate_ragas`

```python
async def evaluate_ragas(records: list[dict[str, Any]], settings: Settings) -> dict[str, Any]
```

**Source:** [app/evaluation/run.py:157](../app/evaluation/run.py#L157)

Evaluate ragas; behavior is defined by the linked implementation.

**Decorators:** None.

**Imported dependencies referenced:** `app.core.config.Settings`, `asyncio`, `math.isfinite`, `openai.AsyncOpenAI`, `ragas.embeddings.OpenAIEmbeddings`, `ragas.llms.llm_factory`, `ragas.metrics.collections.AnswerRelevancy`, `ragas.metrics.collections.ContextPrecision`, `ragas.metrics.collections.ContextRecall`, `ragas.metrics.collections.Faithfulness`, `typing.Any`

**Other calls / relationships:** `ValueError`, `any`, `dict`, `faithfulness.ascore`, `float`, `len`, `precision.ascore`, `recall.ascore`, `relevancy.ascore`, `row.values`, `scores.append`, `settings.openai_api_key.get_secret_value`, `sum`, `zip`.

### `quality_gate`

```python
def quality_gate(report: dict[str, Any], minimum: float | None) -> bool
```

**Source:** [app/evaluation/run.py:215](../app/evaluation/run.py#L215)

Quality gate; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `typing.Any`

**Other calls / relationships:** `all`, `bool`, `list`, `report['ragas']['means'].values`, `values.extend`.

### `publish_datadog_evaluations`

```python
def publish_datadog_evaluations(records: list[dict[str, Any]], ragas: dict[str, Any]) -> int
```

**Source:** [app/evaluation/run.py:231](../app/evaluation/run.py#L231)

Join existing scores to the generation's workflow, including abstention cases.

**Imported dependencies referenced:** `ddtrace.llmobs.LLMObs`, `typing.Any`

**Other calls / relationships:** `iter`, `label.startswith`, `metrics.items`, `metrics.update`, `next`, `next(scores).items`.

### `run`

```python
async def run(cases: list[GoldenCase], settings: Settings) -> dict[str, Any]
```

**Source:** [app/evaluation/run.py:265](../app/evaluation/run.py#L265)

Run; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.chains.prompts.judge.JUDGE_VERSION`, `app.core.config.Settings`, `asyncio`, `datetime.UTC`, `datetime.datetime`, `ddtrace.llmobs.LLMObs`, `importlib.metadata.version`, `typing.Any`

**Other calls / relationships:** `collect_records`, `evaluate_ragas`, `publish_datadog_evaluations`.

### `main`

```python
def main() -> None
```

**Source:** [app/evaluation/run.py:293](../app/evaluation/run.py#L293)

Main; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.config.get_settings`, `app.core.logging.configure_logging`, `argparse`, `asyncio`, `datetime.UTC`, `datetime.datetime`, `json`, `pathlib.Path`, `structlog`

**Other calls / relationships:** `SystemExit`, `args.output.parent.mkdir`, `args.output.write_text`, `len`, `load_cases`, `logger.exception`, `parser.add_argument`, `parser.error`, `parser.parse_args`, `quality_gate`, `run`, `str`, `type`.
