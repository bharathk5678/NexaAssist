# C4 code inventory: app/models

**Language:** Python 3.14. **Scope:** direct modules listed below, with child inventories linked separately.

Strict Pydantic request, response, citation, ingestion and feedback contracts shared across process boundaries.

**Location:** [app/models](../app/models)

## Observability and evaluation relevance

RetrieveTimings and generation_ms are response fields, not automatically Datadog metric series. Extra request/response fields are forbidden by domain models.

## Module `__init__.py`

**Source:** [app/models/__init__.py](../app/models/__init__.py)

**Internal dependencies:** None.

**External / standard-library dependencies:** None.

No top-level functions or classes; module provides the exports above or a package marker.

## Module `answer.py`

**Source:** [app/models/answer.py:1](../app/models/answer.py#L1)

**Internal dependencies:** `app.models.retrieval.Citation`, `app.models.retrieval.RetrieveTimings`

**External / standard-library dependencies:** `datetime.date`, `pydantic.BaseModel`, `pydantic.ConfigDict`, `pydantic.Field`, `typing.Literal`

### Class `EvidenceQuote`

`class EvidenceQuote(BaseModel)` — [app/models/answer.py:11](../app/models/answer.py#L11)

Evidencequote; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
evidence_id: int = Field(ge=1)
quote: str = Field(min_length=1)
```

### Class `AnswerDraft`

`class AnswerDraft(BaseModel)` — [app/models/answer.py:18](../app/models/answer.py#L18)

Model output; source identities are resolved by application code.

Declared fields (inherited fields remain on the linked base class):

```python
status: Literal['answered', 'insufficient_evidence']
answer: str = Field(min_length=1)
evidence: list[EvidenceQuote]
```

### Class `AnswerCitation`

`class AnswerCitation(EvidenceQuote)` — [app/models/answer.py:28](../app/models/answer.py#L28)

Answercitation; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
matched_child: Citation
```

### Class `AnswerResponse`

`class AnswerResponse(BaseModel)` — [app/models/answer.py:33](../app/models/answer.py#L33)

Answerresponse; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
as_of: date
status: Literal['answered', 'insufficient_evidence']
answer: str
citations: list[AnswerCitation]
retrieval_timings: RetrieveTimings
generation_ms: float
```

## Module `feedback.py`

**Source:** [app/models/feedback.py:1](../app/models/feedback.py#L1)

**Internal dependencies:** `app.models.answer.AnswerResponse`, `app.models.retrieval.RetrieveRequest`

**External / standard-library dependencies:** `datetime.datetime`, `pydantic.BaseModel`, `pydantic.ConfigDict`, `pydantic.Field`, `pydantic.model_validator`, `typing.Literal`, `uuid.UUID`

### Class `FeedbackRequest`

`class FeedbackRequest(BaseModel)` — [app/models/feedback.py:13](../app/models/feedback.py#L13)

Feedbackrequest; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
request: RetrieveRequest
response: AnswerResponse
helpful: bool
correction: str = Field(default='', max_length=4000)
```

### `FeedbackRequest.matching_dates`

```python
def matching_dates(self) -> FeedbackRequest
```

**Source:** [app/models/feedback.py:22](../app/models/feedback.py#L22)

Matching dates; behavior is defined by the linked implementation.

**Decorators:** `model_validator(mode='after')`.

**Imported dependencies referenced:** `pydantic.model_validator`

**Other calls / relationships:** `ValueError`.

### Class `FeedbackRecord`

`class FeedbackRecord(FeedbackRequest)` — [app/models/feedback.py:28](../app/models/feedback.py#L28)

Feedbackrecord; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
feedback_id: UUID
created_at: datetime
status: Literal['pending', 'accepted', 'rejected'] = 'pending'
reviewer: str | None = None
review_note: str = ''
```

### Class `FeedbackReview`

`class FeedbackReview(BaseModel)` — [app/models/feedback.py:36](../app/models/feedback.py#L36)

Feedbackreview; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
status: Literal['accepted', 'rejected']
reviewer: str = Field(min_length=1, max_length=100)
review_note: str = Field(min_length=1, max_length=4000)
```

## Module `ingestion.py`

**Source:** [app/models/ingestion.py:1](../app/models/ingestion.py#L1)

**Internal dependencies:** None.

**External / standard-library dependencies:** `datetime.date`, `pydantic.BaseModel`, `pydantic.ConfigDict`

### Class `IngestRequest`

`class IngestRequest(BaseModel)` — [app/models/ingestion.py:8](../app/models/ingestion.py#L8)

Ingestion Service contract: one source document plus its document-level metadata.

The ninth metadata field, section_type, is set per chunk by the pipeline, as are
clause, parent_id and checksum.

Declared fields (inherited fields remain on the linked base class):

```python
source_path: str
doc_id: str
title: str
institution: str
product_id: str | None = None
policy_version: str
effective_date: date
effective_to: date | None = None
supersedes: str | None = None
jurisdiction: str
doc_type: str
confidentiality_level: str
```

### Class `IngestResponse`

`class IngestResponse(BaseModel)` — [app/models/ingestion.py:31](../app/models/ingestion.py#L31)

Ingestresponse; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
doc_id: str
chunk_count: int
chunk_ids: list[str]
embedded_count: int
unchanged_count: int
embedding_model: str
```

## Module `retrieval.py`

**Source:** [app/models/retrieval.py:1](../app/models/retrieval.py#L1)

**Internal dependencies:** None.

**External / standard-library dependencies:** `datetime.date`, `pydantic.BaseModel`, `pydantic.ConfigDict`, `pydantic.Field`

### Class `RetrieveRequest`

`class RetrieveRequest(BaseModel)` — [app/models/retrieval.py:8](../app/models/retrieval.py#L8)

Retrieverequest; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
query: str = Field(min_length=1, max_length=2000)
as_of: date
top_k: int = Field(default=5, ge=1, le=20)
product_id: str | None = Field(default=None, min_length=1)
jurisdiction: str | None = Field(default=None, min_length=1)
```

### Class `Citation`

`class Citation(BaseModel)` — [app/models/retrieval.py:18](../app/models/retrieval.py#L18)

Citation; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
doc_id: str
title: str
policy_version: str
clause: str | None
effective_date: date
```

### Class `RetrieveHit`

`class RetrieveHit(BaseModel)` — [app/models/retrieval.py:28](../app/models/retrieval.py#L28)

Retrievehit; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
rank: int
score: float
text: str
parent_text: str
citation: Citation
```

### Class `RetrieveTimings`

`class RetrieveTimings(BaseModel)` — [app/models/retrieval.py:38](../app/models/retrieval.py#L38)

Retrievetimings; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
search_ms: float
parent_ms: float
total_ms: float
```

### Class `RetrieveResponse`

`class RetrieveResponse(BaseModel)` — [app/models/retrieval.py:46](../app/models/retrieval.py#L46)

Retrieveresponse; behavior is defined by the linked implementation.

Declared fields (inherited fields remain on the linked base class):

```python
as_of: date
results: list[RetrieveHit]
timings: RetrieveTimings
```
