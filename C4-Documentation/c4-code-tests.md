# C4 code inventory: tests

**Language:** Python 3.14. **Scope:** direct modules listed below, with child inventories linked separately.

Unit and integration-style checks with fakes and controlled providers. The telemetry subprocess checks early instrumentation and JSON correlation locally without contacting a Datadog Agent.

**Location:** [tests](../tests)

## Observability and evaluation relevance

Assertions validate local contracts, trace creation and score wiring. They do not prove Datadog cloud ingestion, dashboards, monitor configuration, or live answer quality.

## Module `conftest.py`

**Source:** [tests/conftest.py:1](../tests/conftest.py#L1)

**Internal dependencies:** `app.core.config.Settings`

**External / standard-library dependencies:** `pytest`

### `settings`

```python
def settings() -> Settings
```

**Source:** [tests/conftest.py:9](../tests/conftest.py#L9)

Settings; behavior is defined by the linked implementation.

**Decorators:** `pytest.fixture`.

**Imported dependencies referenced:** `app.core.config.Settings`, `pytest`

## Module `test_answer.py`

**Source:** [tests/test_answer.py:1](../tests/test_answer.py#L1)

**Internal dependencies:** `app.api.answer`, `app.chains.answer.build_answer_chain`, `app.chains.context.assemble_context`, `app.chains.context.render_context`, `app.chains.context.token_encoder`, `app.core.config.Settings`, `app.core.config.get_settings`, `app.main.create_app`, `app.models.retrieval.Citation`, `app.models.retrieval.RetrieveHit`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.models.retrieval.RetrieveTimings`

**External / standard-library dependencies:** `asyncio`, `datetime.date`, `fastapi.testclient.TestClient`, `json`, `langchain_core.language_models.chat_models.BaseChatModel`, `langchain_core.runnables.RunnableLambda`, `pytest`, `typing.Any`, `typing.cast`, `unittest.mock.AsyncMock`, `unittest.mock.Mock`

### `hit`

```python
def hit(number: int=1, text: str='Maximum amount is 7.5 crore.') -> RetrieveHit
```

**Source:** [tests/test_answer.py:28](../tests/test_answer.py#L28)

Hit; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.models.retrieval.Citation`, `app.models.retrieval.RetrieveHit`, `datetime.date`

### `run_answer`

```python
def run_answer(settings: Settings, hits: list[RetrieveHit], draft: dict[str, Any]) -> Any
```

**Source:** [tests/test_answer.py:44](../tests/test_answer.py#L44)

Run answer; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.chains.answer.build_answer_chain`, `app.core.config.Settings`, `app.models.retrieval.RetrieveHit`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.models.retrieval.RetrieveTimings`, `asyncio`, `datetime.date`, `langchain_core.language_models.chat_models.BaseChatModel`, `langchain_core.runnables.RunnableLambda`, `typing.Any`, `typing.cast`, `unittest.mock.Mock`

**Other calls / relationships:** `chain.ainvoke`.

### `test_answer_returns_verified_quote`

```python
def test_answer_returns_verified_quote(settings: Settings) -> None
```

**Source:** [tests/test_answer.py:58](../tests/test_answer.py#L58)

Checks answer returns verified quote.

**Imported dependencies referenced:** `app.core.config.Settings`

**Other calls / relationships:** `hit`, `run_answer`.

### `test_answer_abstains_on_invalid_citations`

```python
def test_answer_abstains_on_invalid_citations(settings: Settings, answer: str, evidence: list[dict[str, Any]]) -> None
```

**Source:** [tests/test_answer.py:82](../tests/test_answer.py#L82)

Checks answer abstains on invalid citations.

**Decorators:** `pytest.mark.parametrize('answer,evidence', [('7.5 crore [2]', [{'evidence_id': 1, 'quote': '7.5 crore'}]), ('7.5 crore [2]', [{'evidence_id': 2, 'quote': '7.5 crore'}]), ('7.5 crore [1]', [{'evidence_id': 1, 'quote': 'invented fee'}]), ('7.5 crore [1]', [{'evidence_id': 1, 'quote': ' '}]), ('7.5 crore', [])])`.

**Imported dependencies referenced:** `app.core.config.Settings`, `pytest`, `typing.Any`

**Other calls / relationships:** `hit`, `run_answer`.

### `test_empty_retrieval_does_not_generate`

```python
def test_empty_retrieval_does_not_generate(settings: Settings) -> None
```

**Source:** [tests/test_answer.py:98](../tests/test_answer.py#L98)

Checks empty retrieval does not generate.

**Imported dependencies referenced:** `app.core.config.Settings`

**Other calls / relationships:** `run_answer`.

### `test_context_budget_deduplicates_and_preserves_whole_passages`

```python
def test_context_budget_deduplicates_and_preserves_whole_passages() -> None
```

**Source:** [tests/test_answer.py:103](../tests/test_answer.py#L103)

Checks context budget deduplicates and preserves whole passages.

**Imported dependencies referenced:** `app.chains.context.assemble_context`, `app.chains.context.render_context`, `app.chains.context.token_encoder`, `json`

**Other calls / relationships:** `all`, `hit`, `hit().model_copy`, `len`, `sources.values`, `token_encoder('o200k_base').encode`.

### `test_context_places_best_two_passages_at_edges`

```python
def test_context_places_best_two_passages_at_edges() -> None
```

**Source:** [tests/test_answer.py:113](../tests/test_answer.py#L113)

Checks context places best two passages at edges.

**Imported dependencies referenced:** `app.chains.context.assemble_context`

**Other calls / relationships:** `hit`, `range`, `sources.values`.

### `test_context_keeps_distinct_children_when_their_shared_parent_is_oversized`

```python
def test_context_keeps_distinct_children_when_their_shared_parent_is_oversized() -> None
```

**Source:** [tests/test_answer.py:118](../tests/test_answer.py#L118)

Checks context keeps distinct children when their shared parent is oversized.

**Imported dependencies referenced:** `app.chains.context.assemble_context`, `app.chains.context.render_context`, `app.chains.context.token_encoder`

**Other calls / relationships:** `first.citation.model_copy`, `first.model_copy`, `hit`, `hit(text='The processing fee is 0.35 percent.').model_copy`, `len`, `sources.values`, `token_encoder('o200k_base').encode`.

### `test_answer_api_validates_and_hides_provider_errors`

```python
def test_answer_api_validates_and_hides_provider_errors(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None
```

**Source:** [tests/test_answer.py:135](../tests/test_answer.py#L135)

Checks answer api validates and hides provider errors.

**Imported dependencies referenced:** `app.api.answer`, `app.core.config.Settings`, `app.core.config.get_settings`, `app.main.create_app`, `fastapi.testclient.TestClient`, `pytest`, `unittest.mock.AsyncMock`

**Other calls / relationships:** `TimeoutError`, `client.post`, `monkeypatch.setattr`.

## Module `test_evaluation.py`

**Source:** [tests/test_evaluation.py:1](../tests/test_evaluation.py#L1)

**Internal dependencies:** `app.core.config.Settings`, `app.evaluation.run`, `app.evaluation.run.JudgeScore`, `app.evaluation.run.load_cases`, `app.evaluation.run.quality_gate`, `app.models.answer.AnswerDraft`, `app.models.retrieval.RetrieveResponse`

**External / standard-library dependencies:** `asyncio`, `contextlib.nullcontext`, `langchain_core.language_models.chat_models.BaseChatModel`, `langchain_core.runnables.RunnableLambda`, `pathlib.Path`, `pydantic.ValidationError`, `pytest`, `ragas.metrics.collections.AnswerRelevancy`, `ragas.metrics.collections.ContextPrecision`, `ragas.metrics.collections.ContextRecall`, `ragas.metrics.collections.Faithfulness`, `types.SimpleNamespace`, `typing.Any`, `unittest.mock.AsyncMock`, `unittest.mock.Mock`

### `test_phase1_cases_include_supported_and_abstention_questions`

```python
def test_phase1_cases_include_supported_and_abstention_questions() -> None
```

**Source:** [tests/test_evaluation.py:18](../tests/test_evaluation.py#L18)

Checks phase1 cases include supported and abstention questions.

**Imported dependencies referenced:** `app.evaluation.run.load_cases`, `pathlib.Path`

**Other calls / relationships:** `all`, `len`, `sum`.

### `test_quality_gate_rejects_low_quality_and_wrong_abstention`

```python
def test_quality_gate_rejects_low_quality_and_wrong_abstention() -> None
```

**Source:** [tests/test_evaluation.py:25](../tests/test_evaluation.py#L25)

Checks quality gate rejects low quality and wrong abstention.

**Imported dependencies referenced:** `app.evaluation.run.JudgeScore`, `app.evaluation.run.quality_gate`, `pydantic.ValidationError`, `pytest`, `typing.Any`

**Other calls / relationships:** `float`.

### `test_ragas_scores_actual_text_and_penalizes_missing_evidence`

```python
def test_ragas_scores_actual_text_and_penalizes_missing_evidence(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None
```

**Source:** [tests/test_evaluation.py:37](../tests/test_evaluation.py#L37)

Checks ragas scores actual text and penalizes missing evidence.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.evaluation.run`, `asyncio`, `pytest`, `ragas.metrics.collections.AnswerRelevancy`, `ragas.metrics.collections.ContextPrecision`, `ragas.metrics.collections.ContextRecall`, `ragas.metrics.collections.Faithfulness`, `types.SimpleNamespace`, `unittest.mock.AsyncMock`

**Other calls / relationships:** `all`, `monkeypatch.setattr`, `monkeypatch.setenv`, `scorers.append`.

### `test_evaluation_reuses_generation_evidence_and_collects_trace`

```python
def test_evaluation_reuses_generation_evidence_and_collects_trace(monkeypatch: pytest.MonkeyPatch, settings: Settings, datadog_enabled: bool) -> None
```

**Source:** [tests/test_evaluation.py:72](../tests/test_evaluation.py#L72)

Checks evaluation reuses generation evidence and collects trace.

**Decorators:** `pytest.mark.parametrize('datadog_enabled', [False, True])`.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.evaluation.run`, `app.evaluation.run.load_cases`, `app.models.answer.AnswerDraft`, `app.models.retrieval.RetrieveResponse`, `asyncio`, `contextlib.nullcontext`, `langchain_core.language_models.chat_models.BaseChatModel`, `langchain_core.runnables.RunnableLambda`, `pathlib.Path`, `pytest`, `types.SimpleNamespace`, `typing.Any`, `unittest.mock.AsyncMock`, `unittest.mock.Mock`

**Other calls / relationships:** `datadog.annotate.assert_not_called`, `datadog.export_span.assert_called_once_with`, `datadog.workflow.assert_not_called`, `monkeypatch.setattr`, `object`.

### `test_evaluation_reuses_generation_evidence_and_collects_trace.structured`

```python
def structured(schema: Any, **_: Any) -> Any
```

**Source:** [tests/test_evaluation.py:117](../tests/test_evaluation.py#L117)

Structured; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.models.answer.AnswerDraft`, `langchain_core.runnables.RunnableLambda`, `typing.Any`

### `test_datadog_scores_join_the_correct_case_and_skip_ragas_for_abstentions`

```python
def test_datadog_scores_join_the_correct_case_and_skip_ragas_for_abstentions(monkeypatch: pytest.MonkeyPatch) -> None
```

**Source:** [tests/test_evaluation.py:159](../tests/test_evaluation.py#L159)

Checks datadog scores join the correct case and skip ragas for abstentions.

**Imported dependencies referenced:** `app.evaluation.run`, `pytest`, `unittest.mock.Mock`

**Other calls / relationships:** `all`, `enumerate`, `label.startswith`, `monkeypatch.setattr`, `str`.

### `test_datadog_export_is_optional_and_flushes_when_enabled`

```python
def test_datadog_export_is_optional_and_flushes_when_enabled(monkeypatch: pytest.MonkeyPatch, settings: Settings, enabled: bool) -> None
```

**Source:** [tests/test_evaluation.py:197](../tests/test_evaluation.py#L197)

Checks datadog export is optional and flushes when enabled.

**Decorators:** `pytest.mark.parametrize('enabled', [False, True])`.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.evaluation.run`, `asyncio`, `pytest`, `types.SimpleNamespace`, `unittest.mock.AsyncMock`, `unittest.mock.Mock`

**Other calls / relationships:** `int`, `monkeypatch.setattr`.

## Module `test_feedback.py`

**Source:** [tests/test_feedback.py:1](../tests/test_feedback.py#L1)

**Internal dependencies:** `app.core.config.Settings`, `app.core.config.get_settings`, `app.database.feedback`, `app.database.mongo`, `app.main.create_app`, `app.models.answer.AnswerResponse`, `app.models.feedback.FeedbackRequest`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveTimings`

**External / standard-library dependencies:** `datetime.date`, `fastapi.testclient.TestClient`, `mongomock`, `pytest`, `typing.Any`, `uuid.uuid4`

### `test_feedback_persists_review_and_prevents_overwriting`

```python
def test_feedback_persists_review_and_prevents_overwriting(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None
```

**Source:** [tests/test_feedback.py:20](../tests/test_feedback.py#L20)

Checks feedback persists review and prevents overwriting.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.core.config.get_settings`, `app.database.feedback`, `app.main.create_app`, `app.models.answer.AnswerResponse`, `app.models.feedback.FeedbackRequest`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveTimings`, `datetime.date`, `fastapi.testclient.TestClient`, `mongomock`, `pytest`, `typing.Any`, `uuid.uuid4`

**Other calls / relationships:** `client.get`, `client.get('/feedback').json`, `client.post`, `monkeypatch.setattr`, `request.model_dump`, `response.json`, `settings.model_copy`.

### `test_retire_document_removes_both_stores_only_in_current_scope`

```python
def test_retire_document_removes_both_stores_only_in_current_scope(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None
```

**Source:** [tests/test_feedback.py:57](../tests/test_feedback.py#L57)

Checks retire document removes both stores only in current scope.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.database.mongo`, `mongomock`, `pytest`, `typing.Any`

**Other calls / relationships:** `monkeypatch.setattr`, `storage.chunks.find_one`, `storage[name].insert_many`.

## Module `test_hybrid_rerank.py`

**Source:** [tests/test_hybrid_rerank.py:1](../tests/test_hybrid_rerank.py#L1)

**Internal dependencies:** `app.chains.rerank.build_rerank_chain`, `app.chains.rerank.completion_probabilities`, `app.chains.rerank.relevance_probability`, `app.core.config.Settings`, `app.database.retrieval.build_hybrid_search`

**External / standard-library dependencies:** `asyncio`, `httpx`, `json`, `langchain_core.documents.Document`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_mongodb.MongoDBAtlasVectorSearch`, `mongomock`, `pytest`, `typing.Any`, `unittest.mock.Mock`

### `test_hybrid_pipeline_filters_both_branches_before_ranking`

```python
def test_hybrid_pipeline_filters_both_branches_before_ranking(settings: Settings) -> None
```

**Source:** [tests/test_hybrid_rerank.py:20](../tests/test_hybrid_rerank.py#L20)

Checks hybrid pipeline filters both branches before ranking.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.database.retrieval.build_hybrid_search`, `asyncio`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_mongodb.MongoDBAtlasVectorSearch`, `mongomock`, `typing.Any`, `unittest.mock.Mock`

**Other calls / relationships:** `build_hybrid_search(store, settings).ainvoke`, `enumerate`, `next`.

### `test_ollama_content_array_logprobs`

```python
def test_ollama_content_array_logprobs() -> None
```

**Source:** [tests/test_hybrid_rerank.py:62](../tests/test_hybrid_rerank.py#L62)

Checks ollama content array logprobs.

**Imported dependencies referenced:** `app.chains.rerank.completion_probabilities`, `app.chains.rerank.relevance_probability`

### `test_local_reranker_uses_openai_completions_and_likelihoods`

```python
def test_local_reranker_uses_openai_completions_and_likelihoods(settings: Settings) -> None
```

**Source:** [tests/test_hybrid_rerank.py:86](../tests/test_hybrid_rerank.py#L86)

Checks local reranker uses openai completions and likelihoods.

**Imported dependencies referenced:** `app.chains.rerank.build_rerank_chain`, `app.core.config.Settings`, `asyncio`, `httpx`, `json`, `langchain_core.documents.Document`

**Other calls / relationships:** `build_rerank_chain(settings, transport=httpx.MockTransport(respond)).ainvoke`, `settings.model_copy`.

### `test_local_reranker_uses_openai_completions_and_likelihoods.respond`

```python
def respond(request: httpx.Request) -> httpx.Response
```

**Source:** [tests/test_hybrid_rerank.py:91](../tests/test_hybrid_rerank.py#L91)

Respond; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `httpx`, `json`

### `test_native_ollama_reranker_uses_raw_scoring_prompt`

```python
def test_native_ollama_reranker_uses_raw_scoring_prompt(settings: Settings) -> None
```

**Source:** [tests/test_hybrid_rerank.py:137](../tests/test_hybrid_rerank.py#L137)

Checks native ollama reranker uses raw scoring prompt.

**Imported dependencies referenced:** `app.chains.rerank.build_rerank_chain`, `app.core.config.Settings`, `asyncio`, `httpx`, `json`, `langchain_core.documents.Document`

**Other calls / relationships:** `build_rerank_chain(settings, transport=httpx.MockTransport(respond)).ainvoke`.

### `test_native_ollama_reranker_uses_raw_scoring_prompt.respond`

```python
def respond(request: httpx.Request) -> httpx.Response
```

**Source:** [tests/test_hybrid_rerank.py:138](../tests/test_hybrid_rerank.py#L138)

Respond; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `httpx`, `json`

### `test_missing_or_invalid_local_likelihoods_do_not_fabricate_scores`

```python
def test_missing_or_invalid_local_likelihoods_do_not_fabricate_scores(probabilities: dict[str, float]) -> None
```

**Source:** [tests/test_hybrid_rerank.py:170](../tests/test_hybrid_rerank.py#L170)

Checks missing or invalid local likelihoods do not fabricate scores.

**Decorators:** `pytest.mark.parametrize('probabilities', [{'yes': -0.1}, {'yes': float('nan'), 'no': -1}])`.

**Imported dependencies referenced:** `app.chains.rerank.relevance_probability`, `pytest`

**Other calls / relationships:** `float`.

### `test_case_and_whitespace_variants_do_not_replace_qwen_scoring_tokens`

```python
def test_case_and_whitespace_variants_do_not_replace_qwen_scoring_tokens() -> None
```

**Source:** [tests/test_hybrid_rerank.py:177](../tests/test_hybrid_rerank.py#L177)

Checks case and whitespace variants do not replace qwen scoring tokens.

**Imported dependencies referenced:** `app.chains.rerank.relevance_probability`

### `test_case_variants_cannot_substitute_for_missing_exact_qwen_tokens`

```python
def test_case_variants_cannot_substitute_for_missing_exact_qwen_tokens() -> None
```

**Source:** [tests/test_hybrid_rerank.py:183](../tests/test_hybrid_rerank.py#L183)

Checks case variants cannot substitute for missing exact qwen tokens.

**Imported dependencies referenced:** `app.chains.rerank.relevance_probability`, `pytest`

## Module `test_ingestion.py`

**Source:** [tests/test_ingestion.py:1](../tests/test_ingestion.py#L1)

**Internal dependencies:** `app.chains.chunking.chunk_by_clause`, `app.chains.ingestion.build_ingestion_chain`, `app.core.config.Settings`, `app.database.mongo.delete_stale_chunks`, `app.models.ingestion.IngestRequest`, `app.models.ingestion.IngestResponse`, `app.services.ingestion.requests_from_register`

**External / standard-library dependencies:** `asyncio`, `datetime.date`, `itertools.pairwise`, `json`, `langchain_core.documents.Document`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_core.stores.InMemoryStore`, `langchain_core.vectorstores.InMemoryVectorStore`, `mongomock`, `pathlib.Path`, `pytest`, `typing.Any`, `unstructured.documents.elements.Element`, `unstructured.documents.elements.ElementMetadata`, `unstructured.documents.elements.ListItem`, `unstructured.documents.elements.NarrativeText`, `unstructured.documents.elements.Table`, `unstructured.documents.elements.Title`

**Module state / exports:** `REGISTER`, `GOLDEN_QA`, `METADATA_FIELDS`.

### `settings`

```python
def settings() -> Settings
```

**Source:** [tests/test_ingestion.py:51](../tests/test_ingestion.py#L51)

Settings; behavior is defined by the linked implementation.

**Decorators:** `pytest.fixture(scope='module')`.

**Imported dependencies referenced:** `app.core.config.Settings`, `pytest`

### `requests`

```python
def requests(settings: Settings) -> dict[str, IngestRequest]
```

**Source:** [tests/test_ingestion.py:65](../tests/test_ingestion.py#L65)

Requests; behavior is defined by the linked implementation.

**Decorators:** `pytest.fixture(scope='module')`.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `app.services.ingestion.requests_from_register`, `pytest`

### Class `CountingEmbedding`

`class CountingEmbedding(DeterministicFakeEmbedding)` — [tests/test_ingestion.py:69](../tests/test_ingestion.py#L69)

Fake embeddings that record how many texts were sent to the model.

Declared fields (inherited fields remain on the linked base class):

```python
embedded: int = 0
```

### `CountingEmbedding.embed_documents`

```python
def embed_documents(self, texts: list[str]) -> list[list[float]]
```

**Source:** [tests/test_ingestion.py:74](../tests/test_ingestion.py#L74)

Embed documents; behavior is defined by the linked implementation.

**Imported dependencies referenced:** None directly.

**Other calls / relationships:** `len`, `super`, `super().embed_documents`.

### `run_chain`

```python
def run_chain(store: InMemoryVectorStore, settings: Settings, request: IngestRequest, parents: InMemoryStore | None=None) -> IngestResponse
```

**Source:** [tests/test_ingestion.py:79](../tests/test_ingestion.py#L79)

Run chain; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.chains.ingestion.build_ingestion_chain`, `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `app.models.ingestion.IngestResponse`, `asyncio`, `langchain_core.stores.InMemoryStore`, `langchain_core.vectorstores.InMemoryVectorStore`

**Other calls / relationships:** `chain.ainvoke`, `len`.

### `ingest`

```python
def ingest(store: InMemoryVectorStore, settings: Settings, request: IngestRequest, parents: InMemoryStore | None=None) -> list[Document]
```

**Source:** [tests/test_ingestion.py:92](../tests/test_ingestion.py#L92)

Ingest; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `langchain_core.documents.Document`, `langchain_core.stores.InMemoryStore`, `langchain_core.vectorstores.InMemoryVectorStore`

**Other calls / relationships:** `run_chain`, `store.get_by_ids`.

### `home_loan_v3`

```python
def home_loan_v3(settings: Settings, requests: dict[str, IngestRequest]) -> list[Document]
```

**Source:** [tests/test_ingestion.py:102](../tests/test_ingestion.py#L102)

Home loan v3; behavior is defined by the linked implementation.

**Decorators:** `pytest.fixture(scope='module')`.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `langchain_core.documents.Document`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_core.vectorstores.InMemoryVectorStore`, `pytest`

**Other calls / relationships:** `ingest`.

### `test_register_maps_to_requests`

```python
def test_register_maps_to_requests(requests: dict[str, IngestRequest]) -> None
```

**Source:** [tests/test_ingestion.py:107](../tests/test_ingestion.py#L107)

Checks register maps to requests.

**Imported dependencies referenced:** `app.models.ingestion.IngestRequest`, `datetime.date`

**Other calls / relationships:** `circular.effective_date.isoformat`, `len`.

### `test_every_document_parses_and_chunks`

```python
def test_every_document_parses_and_chunks(settings: Settings, requests: dict[str, IngestRequest]) -> None
```

**Source:** [tests/test_ingestion.py:116](../tests/test_ingestion.py#L116)

Checks every document parses and chunks.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_core.vectorstores.InMemoryVectorStore`

**Other calls / relationships:** `document.metadata.keys`, `document.metadata['chunk_id'].startswith`, `ingest`, `requests.values`.

### `test_version_metadata_is_stamped_on_every_chunk`

```python
def test_version_metadata_is_stamped_on_every_chunk(home_loan_v3: list[Document]) -> None
```

**Source:** [tests/test_ingestion.py:128](../tests/test_ingestion.py#L128)

Checks version metadata is stamped on every chunk.

**Imported dependencies referenced:** `langchain_core.documents.Document`

### `test_expired_document_keeps_indexable_end_date`

```python
def test_expired_document_keeps_indexable_end_date(settings: Settings, requests: dict[str, IngestRequest]) -> None
```

**Source:** [tests/test_ingestion.py:138](../tests/test_ingestion.py#L138)

Checks expired document keeps indexable end date.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_core.vectorstores.InMemoryVectorStore`

**Other calls / relationships:** `ingest`.

### `test_tables_are_kept_whole`

```python
def test_tables_are_kept_whole(home_loan_v3: list[Document]) -> None
```

**Source:** [tests/test_ingestion.py:147](../tests/test_ingestion.py#L147)

Checks tables are kept whole.

**Imported dependencies referenced:** `langchain_core.documents.Document`

**Other calls / relationships:** `next`.

### `test_running_headers_and_footers_are_dropped`

```python
def test_running_headers_and_footers_are_dropped(home_loan_v3: list[Document]) -> None
```

**Source:** [tests/test_ingestion.py:160](../tests/test_ingestion.py#L160)

Checks running headers and footers are dropped.

**Imported dependencies referenced:** `langchain_core.documents.Document`

**Other calls / relationships:** `'\n'.join`.

### `test_reingesting_is_idempotent`

```python
def test_reingesting_is_idempotent(settings: Settings, requests: dict[str, IngestRequest]) -> None
```

**Source:** [tests/test_ingestion.py:167](../tests/test_ingestion.py#L167)

Checks reingesting is idempotent.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_core.vectorstores.InMemoryVectorStore`

**Other calls / relationships:** `ingest`, `len`.

### `test_every_registered_clause_is_exactly_one_chunk`

```python
def test_every_registered_clause_is_exactly_one_chunk(settings: Settings, requests: dict[str, IngestRequest]) -> None
```

**Source:** [tests/test_ingestion.py:176](../tests/test_ingestion.py#L176)

Checks every registered clause is exactly one chunk.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `json`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_core.vectorstores.InMemoryVectorStore`

**Other calls / relationships:** `REGISTER.read_text`, `ingest`, `sorted`.

### `test_every_golden_citation_resolves_to_a_chunk`

```python
def test_every_golden_citation_resolves_to_a_chunk(settings: Settings, requests: dict[str, IngestRequest]) -> None
```

**Source:** [tests/test_ingestion.py:187](../tests/test_ingestion.py#L187)

Checks every golden citation resolves to a chunk.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `json`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_core.vectorstores.InMemoryVectorStore`

**Other calls / relationships:** `GOLDEN_QA.read_text`, `GOLDEN_QA.read_text().splitlines`, `ingest`, `requests.values`.

### `test_chunk_carries_identity_header_and_clause_id`

```python
def test_chunk_carries_identity_header_and_clause_id(home_loan_v3: list[Document]) -> None
```

**Source:** [tests/test_ingestion.py:205](../tests/test_ingestion.py#L205)

Checks chunk carries identity header and clause id.

**Imported dependencies referenced:** `langchain_core.documents.Document`

**Other calls / relationships:** `fee.page_content.startswith`, `next`.

### `test_oversized_clause_splits_narrative_with_overlap_but_never_the_table`

```python
def test_oversized_clause_splits_narrative_with_overlap_but_never_the_table() -> None
```

**Source:** [tests/test_ingestion.py:216](../tests/test_ingestion.py#L216)

Checks oversized clause splits narrative with overlap but never the table.

**Imported dependencies referenced:** `app.chains.chunking.chunk_by_clause`, `itertools.pairwise`, `unstructured.documents.elements.Element`, `unstructured.documents.elements.ElementMetadata`, `unstructured.documents.elements.NarrativeText`, `unstructured.documents.elements.Table`, `unstructured.documents.elements.Title`

**Other calls / relationships:** `' '.join`, `all`, `current.text.split`, `current.text.split('. ')[0].rstrip`, `len`, `previous.text.rstrip`, `previous.text.rstrip().endswith`, `range`.

### `test_oversized_list_clause_is_packed_not_split_per_item`

```python
def test_oversized_list_clause_is_packed_not_split_per_item() -> None
```

**Source:** [tests/test_ingestion.py:243](../tests/test_ingestion.py#L243)

Checks oversized list clause is packed not split per item.

**Imported dependencies referenced:** `app.chains.chunking.chunk_by_clause`, `unstructured.documents.elements.Element`, `unstructured.documents.elements.ListItem`, `unstructured.documents.elements.NarrativeText`, `unstructured.documents.elements.Title`

**Other calls / relationships:** `'\n'.join`, `all`, `chunks[0].text.startswith`, `len`, `range`.

### `test_parent_section_holds_every_clause_of_the_section`

```python
def test_parent_section_holds_every_clause_of_the_section(settings: Settings, requests: dict[str, IngestRequest]) -> None
```

**Source:** [tests/test_ingestion.py:261](../tests/test_ingestion.py#L261)

Checks parent section holds every clause of the section.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_core.stores.InMemoryStore`, `langchain_core.vectorstores.InMemoryVectorStore`

**Other calls / relationships:** `ingest`, `next`, `parents.mget`.

### `test_reingesting_replaces_parent_sections`

```python
def test_reingesting_replaces_parent_sections(settings: Settings, requests: dict[str, IngestRequest]) -> None
```

**Source:** [tests/test_ingestion.py:283](../tests/test_ingestion.py#L283)

Checks reingesting replaces parent sections.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_core.stores.InMemoryStore`, `langchain_core.vectorstores.InMemoryVectorStore`

**Other calls / relationships:** `ingest`, `parents.yield_keys`, `sorted`.

### `test_empty_parse_preserves_existing_chunks_and_parents`

```python
def test_empty_parse_preserves_existing_chunks_and_parents(settings: Settings, requests: dict[str, IngestRequest], monkeypatch: pytest.MonkeyPatch) -> None
```

**Source:** [tests/test_ingestion.py:294](../tests/test_ingestion.py#L294)

Checks empty parse preserves existing chunks and parents.

**Imported dependencies referenced:** `app.chains.ingestion.build_ingestion_chain`, `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `asyncio`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_core.stores.InMemoryStore`, `langchain_core.vectorstores.InMemoryVectorStore`, `pytest`

**Other calls / relationships:** `chain.ainvoke`, `ingest`, `monkeypatch.setattr`, `parents.yield_keys`, `sorted`, `store.get_by_ids`.

### `test_only_new_or_changed_chunks_are_embedded`

```python
def test_only_new_or_changed_chunks_are_embedded(settings: Settings, requests: dict[str, IngestRequest]) -> None
```

**Source:** [tests/test_ingestion.py:313](../tests/test_ingestion.py#L313)

Checks only new or changed chunks are embedded.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `langchain_core.vectorstores.InMemoryVectorStore`

**Other calls / relationships:** `CountingEmbedding`, `run_chain`, `store.get_by_ids`.

### `test_changing_the_embedding_model_re_embeds_everything`

```python
def test_changing_the_embedding_model_re_embeds_everything(settings: Settings, requests: dict[str, IngestRequest]) -> None
```

**Source:** [tests/test_ingestion.py:334](../tests/test_ingestion.py#L334)

Checks changing the embedding model re embeds everything.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_core.vectorstores.InMemoryVectorStore`

**Other calls / relationships:** `run_chain`, `settings.model_copy`.

### `test_stale_chunks_are_deleted_and_current_ones_kept`

```python
def test_stale_chunks_are_deleted_and_current_ones_kept() -> None
```

**Source:** [tests/test_ingestion.py:344](../tests/test_ingestion.py#L344)

Checks stale chunks are deleted and current ones kept.

**Imported dependencies referenced:** `app.database.mongo.delete_stale_chunks`, `mongomock`, `typing.Any`

**Other calls / relationships:** `collection.find`, `collection.insert_many`, `sorted`.

### `test_dimension_change_reembeds_every_chunk`

```python
def test_dimension_change_reembeds_every_chunk(settings: Settings, requests: dict[str, IngestRequest]) -> None
```

**Source:** [tests/test_ingestion.py:357](../tests/test_ingestion.py#L357)

Checks dimension change reembeds every chunk.

**Imported dependencies referenced:** `app.core.config.Settings`, `app.models.ingestion.IngestRequest`, `langchain_core.embeddings.DeterministicFakeEmbedding`, `langchain_core.vectorstores.InMemoryVectorStore`

**Other calls / relationships:** `all`, `run_chain`, `settings.model_copy`, `store.get_by_ids`.

## Module `test_rag_failure_modes.py`

**Source:** [tests/test_rag_failure_modes.py:1](../tests/test_rag_failure_modes.py#L1)

**Internal dependencies:** `app.evaluation.rag_failure_modes.ChunkSnapshot`, `app.evaluation.rag_failure_modes.demo_report`, `app.evaluation.rag_failure_modes.diagnose_embeddings`, `app.evaluation.rag_failure_modes.diagnose_staleness`

**External / standard-library dependencies:** `pytest`

### `test_demo_distinguishes_misses_staleness_and_compatibility`

```python
def test_demo_distinguishes_misses_staleness_and_compatibility() -> None
```

**Source:** [tests/test_rag_failure_modes.py:13](../tests/test_rag_failure_modes.py#L13)

Checks demo distinguishes misses staleness and compatibility.

**Imported dependencies referenced:** `app.evaluation.rag_failure_modes.demo_report`

**Other calls / relationships:** `isinstance`.

### `test_unknown_snapshots_do_not_report_healthy`

```python
def test_unknown_snapshots_do_not_report_healthy() -> None
```

**Source:** [tests/test_rag_failure_modes.py:39](../tests/test_rag_failure_modes.py#L39)

Checks unknown snapshots do not report healthy.

**Imported dependencies referenced:** `app.evaluation.rag_failure_modes.ChunkSnapshot`, `app.evaluation.rag_failure_modes.diagnose_embeddings`, `app.evaluation.rag_failure_modes.diagnose_staleness`, `pytest`

### `test_reject_duplicate_chunk_ids_and_invalid_embedding_contract`

```python
def test_reject_duplicate_chunk_ids_and_invalid_embedding_contract() -> None
```

**Source:** [tests/test_rag_failure_modes.py:51](../tests/test_rag_failure_modes.py#L51)

Checks reject duplicate chunk ids and invalid embedding contract.

**Imported dependencies referenced:** `app.evaluation.rag_failure_modes.ChunkSnapshot`, `app.evaluation.rag_failure_modes.diagnose_embeddings`, `app.evaluation.rag_failure_modes.diagnose_staleness`, `pytest`

## Module `test_retrieval.py`

**Source:** [tests/test_retrieval.py:1](../tests/test_retrieval.py#L1)

**Internal dependencies:** `app.api.retrieval`, `app.chains.retrieval.build_retrieval_chain`, `app.core.config.Settings`, `app.core.config.get_settings`, `app.main.create_app`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.models.retrieval.RetrieveTimings`, `app.services.retrieval`

**External / standard-library dependencies:** `asyncio`, `datetime.date`, `fastapi.testclient.TestClient`, `langchain_core.documents.Document`, `langchain_core.stores.InMemoryStore`, `langchain_core.vectorstores.VectorStore`, `pydantic.ValidationError`, `typing.Any`, `typing.cast`, `unittest.mock.AsyncMock`, `unittest.mock.Mock`

### `settings`

```python
def settings() -> Settings
```

**Source:** [tests/test_retrieval.py:22](../tests/test_retrieval.py#L22)

Settings; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `app.core.config.Settings`

### `test_retrieval_filters_and_expands_parent`

```python
def test_retrieval_filters_and_expands_parent() -> None
```

**Source:** [tests/test_retrieval.py:35](../tests/test_retrieval.py#L35)

Checks retrieval filters and expands parent.

**Imported dependencies referenced:** `app.chains.retrieval.build_retrieval_chain`, `app.models.retrieval.RetrieveRequest`, `asyncio`, `datetime.date`, `langchain_core.documents.Document`, `langchain_core.stores.InMemoryStore`, `langchain_core.vectorstores.VectorStore`, `typing.cast`, `unittest.mock.AsyncMock`, `unittest.mock.Mock`

**Other calls / relationships:** `build_retrieval_chain(cast(VectorStore, store), parents, settings()).ainvoke`, `parents.amset`, `settings`.

### `test_retrieval_empty_and_missing_parent`

```python
def test_retrieval_empty_and_missing_parent() -> None
```

**Source:** [tests/test_retrieval.py:79](../tests/test_retrieval.py#L79)

Checks retrieval empty and missing parent.

**Imported dependencies referenced:** `app.chains.retrieval.build_retrieval_chain`, `app.models.retrieval.RetrieveRequest`, `asyncio`, `datetime.date`, `langchain_core.documents.Document`, `langchain_core.stores.InMemoryStore`, `langchain_core.vectorstores.VectorStore`, `typing.cast`, `unittest.mock.AsyncMock`, `unittest.mock.Mock`

**Other calls / relationships:** `chain.ainvoke`, `settings`.

### `test_request_rejects_invalid_input`

```python
def test_request_rejects_invalid_input() -> None
```

**Source:** [tests/test_retrieval.py:102](../tests/test_retrieval.py#L102)

Checks request rejects invalid input.

**Imported dependencies referenced:** `app.models.retrieval.RetrieveRequest`, `pydantic.ValidationError`

**Other calls / relationships:** `AssertionError`.

### `test_api_returns_safe_failure_and_validates_body`

```python
def test_api_returns_safe_failure_and_validates_body(monkeypatch: Any) -> None
```

**Source:** [tests/test_retrieval.py:115](../tests/test_retrieval.py#L115)

Checks api returns safe failure and validates body.

**Imported dependencies referenced:** `app.api.retrieval`, `app.core.config.get_settings`, `app.main.create_app`, `app.models.retrieval.RetrieveResponse`, `app.models.retrieval.RetrieveTimings`, `datetime.date`, `fastapi.testclient.TestClient`, `typing.Any`, `unittest.mock.AsyncMock`

**Other calls / relationships:** `RuntimeError`, `client.post`, `client.post('/retrieve', json={'query': 'fee', 'as_of': '2026-10-01'}).json`, `monkeypatch.setattr`.

### `test_health_metrics_and_failure_counters`

```python
def test_health_metrics_and_failure_counters(monkeypatch: Any) -> None
```

**Source:** [tests/test_retrieval.py:140](../tests/test_retrieval.py#L140)

Checks health metrics and failure counters.

**Imported dependencies referenced:** `app.main.create_app`, `app.models.retrieval.RetrieveRequest`, `app.models.retrieval.RetrieveResponse`, `app.models.retrieval.RetrieveTimings`, `app.services.retrieval`, `asyncio`, `datetime.date`, `fastapi.testclient.TestClient`, `typing.Any`, `unittest.mock.AsyncMock`, `unittest.mock.Mock`

**Other calls / relationships:** `AssertionError`, `RuntimeError`, `client.get`, `client.get('/health').json`, `client.get('/metrics').json`, `client.get('/metrics/latency').json`, `monkeypatch.setattr`, `object`, `settings`.

## Module `test_telemetry.py`

**Source:** [tests/test_telemetry.py:1](../tests/test_telemetry.py#L1)

**Internal dependencies:** None.

**External / standard-library dependencies:** `json`, `os`, `pathlib.Path`, `subprocess`, `sys`

### `test_early_datadog_instrumentation_traces_api_and_correlates_json_logs`

```python
def test_early_datadog_instrumentation_traces_api_and_correlates_json_logs() -> None
```

**Source:** [tests/test_telemetry.py:10](../tests/test_telemetry.py#L10)

Checks early datadog instrumentation traces api and correlates json logs.

**Imported dependencies referenced:** `json`, `os`, `pathlib.Path`, `subprocess`, `sys`

**Other calls / relationships:** `Path(__file__).resolve`, `Path(sys.executable).with_name`, `any`, `line.startswith`, `next`, `record.get`, `result.stdout.splitlines`, `str`.

## Module `test_ui.py`

**Source:** [tests/test_ui.py:1](../tests/test_ui.py#L1)

**Internal dependencies:** `app.api.answer`, `app.api.retrieval`, `app.core.config.Settings`, `app.core.config.get_settings`, `app.database.feedback`, `app.main`, `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveResponse`, `app.ui.app`

**External / standard-library dependencies:** `collections.abc.Iterator`, `datetime.date`, `fastapi.testclient.TestClient`, `httpx`, `mongomock`, `pathlib.Path`, `pytest`, `starlette.routing.compile_path`, `streamlit.testing.v1.AppTest`, `typing.Any`, `unittest.mock.AsyncMock`

### `client`

```python
def client(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> Iterator[httpx.Client]
```

**Source:** [tests/test_ui.py:29](../tests/test_ui.py#L29)

Client; behavior is defined by the linked implementation.

**Decorators:** `pytest.fixture`.

**Imported dependencies referenced:** `app.api.answer`, `app.api.retrieval`, `app.core.config.Settings`, `app.core.config.get_settings`, `app.database.feedback`, `app.main`, `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveResponse`, `app.ui.app`, `collections.abc.Iterator`, `fastapi.testclient.TestClient`, `httpx`, `mongomock`, `pytest`, `typing.Any`, `unittest.mock.AsyncMock`

**Other calls / relationships:** `asgi_client.request`, `monkeypatch.setattr`, `retrieved.results[0].citation.model_dump`, `retrieved.timings.model_dump`, `str`.

### `client.dispatch`

```python
def dispatch(request: httpx.Request) -> httpx.Response
```

**Source:** [tests/test_ui.py:76](../tests/test_ui.py#L76)

Dispatch; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `httpx`

**Other calls / relationships:** `asgi_client.request`, `str`.

### `test_existing_ui_endpoint_coverage`

```python
def test_existing_ui_endpoint_coverage(client: httpx.Client, decision: str) -> None
```

**Source:** [tests/test_ui.py:95](../tests/test_ui.py#L95)

Checks existing ui endpoint coverage.

**Decorators:** `pytest.mark.parametrize('decision', ['accepted', 'rejected'])`.

**Imported dependencies referenced:** `app.main`, `datetime.date`, `httpx`, `pathlib.Path`, `pytest`, `starlette.routing.compile_path`, `streamlit.testing.v1.AppTest`

**Other calls / relationships:** `Path('app/streamlit_app.py').resolve`, `any`, `app.chat_input[0].set_value`, `app.chat_input[0].set_value('What is the loan limit?').run`, `app.date_input[0].set_value`, `app.radio`, `app.radio(key='workspace').set_value`, `app.radio(key='workspace').set_value('Policy chat').run`, `app.radio(key='workspace').set_value('Review feedback').run`, `app.segmented_control`, `app.segmented_control(key='response_mode').set_value`, `app.selectbox[0].select`, `client.event_hooks['response'].append`, `len`, `method.upper`, `next`, `next((button for button in app.button if button.label == 'Load feedback for review')).click`, `next((button for button in app.button if button.label == 'Load feedback for review')).click().run`, `next((button for button in app.button if button.label == 'Save review')).click`, `next((button for button in app.button if button.label == 'Save review')).click().run`, `next((button for button in app.button if button.label == 'Send feedback')).click`, `next((button for button in app.button if button.label == 'Send feedback')).click().run`, `next((widget for widget in app.text_area if widget.label == 'Review note')).input`, `next((widget for widget in app.text_input if widget.label == 'Reviewer name')).input`, `paths.items`, `pattern.fullmatch`, `responses[-1].json`, `set`, `uncovered.add`.

### `test_ui_reports_service_unavailability`

```python
def test_ui_reports_service_unavailability(monkeypatch: pytest.MonkeyPatch, client: httpx.Client) -> None
```

**Source:** [tests/test_ui.py:160](../tests/test_ui.py#L160)

Checks ui reports service unavailability.

**Imported dependencies referenced:** `httpx`, `pathlib.Path`, `pytest`, `streamlit.testing.v1.AppTest`, `typing.Any`

**Other calls / relationships:** `Path('app/streamlit_app.py').resolve`, `app.chat_input[0].set_value`, `app.chat_input[0].set_value('What is the fee?').run`, `monkeypatch.setattr`.

### `test_ui_reports_service_unavailability.unavailable`

```python
def unavailable(*args: Any, **kwargs: Any) -> httpx.Response
```

**Source:** [tests/test_ui.py:163](../tests/test_ui.py#L163)

Unavailable; behavior is defined by the linked implementation.

**Imported dependencies referenced:** `httpx`, `typing.Any`

### `test_chat_history_filters_and_feedback_are_isolated`

```python
def test_chat_history_filters_and_feedback_are_isolated(client: httpx.Client) -> None
```

**Source:** [tests/test_ui.py:174](../tests/test_ui.py#L174)

Checks chat history filters and feedback are isolated.

**Imported dependencies referenced:** `datetime.date`, `httpx`, `pathlib.Path`, `streamlit.testing.v1.AppTest`

**Other calls / relationships:** `Path('app/streamlit_app.py').resolve`, `app.button`, `app.button(key='new_chat').click`, `app.button(key='new_chat').click().run`, `app.button(key=f'chat_{first_chat}').click`, `app.button(key=f'chat_{first_chat}').click().run`, `app.chat_input[0].set_value`, `app.chat_input[0].set_value('Another policy question').run`, `app.chat_input[0].set_value('What about processing fees?').run`, `app.chat_input[0].set_value('What is the loan limit?').run`, `app.date_input`, `app.date_input(key='policy_date').set_value`, `app.slider`, `app.slider(key='source_count').set_value`, `app.text_area[0].input`, `app.text_input`, `app.text_input(key='product_id').input`, `client.event_hooks['response'].append`, `len`, `next`, `next((button for button in app.button if button.label == 'Send feedback')).click`, `next((button for button in app.button if button.label == 'Send feedback')).click().run`, `next((widget for widget in app.radio if widget.label == 'Was this answer helpful?')).set_value`, `responses[-1].json`.

### `test_failed_question_retries_original_scope`

```python
def test_failed_question_retries_original_scope(monkeypatch: pytest.MonkeyPatch, client: httpx.Client) -> None
```

**Source:** [tests/test_ui.py:217](../tests/test_ui.py#L217)

Checks failed question retries original scope.

**Imported dependencies referenced:** `httpx`, `pathlib.Path`, `pytest`, `streamlit.testing.v1.AppTest`

**Other calls / relationships:** `Path('app/streamlit_app.py').resolve`, `app.chat_input[0].set_value`, `app.chat_input[0].set_value('What is the limit?').run`, `app.text_input`, `app.text_input(key='product_id').input`, `app.text_input(key='product_id').input('NEXA-AL').run`, `len`, `monkeypatch.setattr`, `next`, `next((button for button in app.button if button.label == 'Try again')).click`, `next((button for button in app.button if button.label == 'Try again')).click().run`.

### `test_suggestion_and_blank_input`

```python
def test_suggestion_and_blank_input(client: httpx.Client) -> None
```

**Source:** [tests/test_ui.py:244](../tests/test_ui.py#L244)

Checks suggestion and blank input.

**Imported dependencies referenced:** `httpx`, `pathlib.Path`, `streamlit.testing.v1.AppTest`

**Other calls / relationships:** `Path('app/streamlit_app.py').resolve`, `any`, `app.chat_input[0].set_value`, `app.chat_input[0].set_value('   ').run`, `client.event_hooks['response'].append`, `len`, `next`, `next((button for button in app.button if button.label == 'Home loan limits')).click`, `next((button for button in app.button if button.label == 'Home loan limits')).click().run`.
