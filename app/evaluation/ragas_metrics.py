"""RAGAS collections API, using the existing LangChain provider configuration."""

from __future__ import annotations

from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel
from ragas.embeddings.base import BaseRagasEmbedding
from ragas.llms.base import InstructorBaseRagasLLM
from ragas.metrics.collections import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness


class StructuredJudge(InstructorBaseRagasLLM):
    """Keep RAGAS on the same Responses API path as answer generation."""

    def __init__(self, llm: BaseChatModel) -> None:
        self.llm = llm

    def generate[T: BaseModel](self, prompt: str, response_model: type[T]) -> T:
        raw = self.llm.with_structured_output(
            response_model, method="json_schema", strict=True
        ).invoke(prompt)
        return response_model.model_validate(raw)

    async def agenerate[T: BaseModel](self, prompt: str, response_model: type[T]) -> T:
        raw = await self.llm.with_structured_output(
            response_model, method="json_schema", strict=True
        ).ainvoke(prompt)
        return response_model.model_validate(raw)


class MetricEmbeddings(BaseRagasEmbedding):
    def __init__(self, embeddings: Embeddings) -> None:
        super().__init__()
        self.embeddings = embeddings

    def embed_text(self, text: str, **kwargs: Any) -> list[float]:
        return self.embeddings.embed_query(text)

    async def aembed_text(self, text: str, **kwargs: Any) -> list[float]:
        return await self.embeddings.aembed_query(text)


class RagasScorer:
    def __init__(self, llm: BaseChatModel, embeddings: Embeddings) -> None:
        judge = StructuredJudge(llm)
        self.metrics = {
            "faithfulness": Faithfulness(llm=judge),
            "answer_relevancy": AnswerRelevancy(llm=judge, embeddings=MetricEmbeddings(embeddings)),
            "context_precision": ContextPrecision(llm=judge),
            "context_recall": ContextRecall(llm=judge),
        }
