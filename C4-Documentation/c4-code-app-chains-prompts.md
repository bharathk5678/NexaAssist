# C4 code inventory: app/chains/prompts

**Language:** Python 3.14. **Scope:** direct modules listed below, with child inventories linked separately.

Prompt assets for citation-grounded policy answers, policy judges and Qwen-style reranking. Prompt templates are libraries inside their callers, not deployable services.

**Location:** [app/chains/prompts](../app/chains/prompts)

## Observability and evaluation relevance

JUDGE_VERSION identifies the numeric judge prompt shared by the active evaluation runner. Prompts and evidence affect reproducibility. The unused advisory-verdict prompt was removed during the 20 October cleanup.

## Module `__init__.py`

**Source:** [app/chains/prompts/__init__.py:1](../app/chains/prompts/__init__.py#L1)

Prompts used by the Layer 1 chains.

**Internal dependencies:** None.

**External / standard-library dependencies:** None.

No top-level functions or classes; module provides the exports above or a package marker.

## Module `answer.py`

**Source:** [app/chains/prompts/answer.py:1](../app/chains/prompts/answer.py#L1)

**Internal dependencies:** None.

**External / standard-library dependencies:** `langchain_core.prompts.ChatPromptTemplate`

**Module state / exports:** `ANSWER_PROMPT`.

No top-level functions or classes; module provides the exports above or a package marker.

## Module `judge.py`

**Source:** [app/chains/prompts/judge.py:1](../app/chains/prompts/judge.py#L1)

**Internal dependencies:** None.

**External / standard-library dependencies:** `langchain_core.prompts.ChatPromptTemplate`

**Module state / exports:** `JUDGE_VERSION`, `JUDGE_PROMPT`.

No top-level functions or classes; module provides the exports above or a package marker.

## Module `rerank.py`

**Source:** [app/chains/prompts/rerank.py:1](../app/chains/prompts/rerank.py#L1)

**Internal dependencies:** None.

**External / standard-library dependencies:** None.

### `rerank_prompt`

```python
def rerank_prompt(query: str, document: str, as_of: str) -> str
```

**Source:** [app/chains/prompts/rerank.py:4](../app/chains/prompts/rerank.py#L4)

Qwen3's official yes/no scoring format, with policy-specific instructions.

https://huggingface.co/Qwen/Qwen3-Reranker-0.6B

**Imported dependencies referenced:** None directly.
