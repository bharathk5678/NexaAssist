from __future__ import annotations

from contextlib import nullcontext

import structlog
from ddtrace.llmobs import LLMObs
from langchain_core.runnables import RunnableLambda

from app.chains.answer import build_answer_chain
from app.chains.llm import get_chat_model
from app.core.config import Settings
from app.models.answer import AnswerResponse
from app.models.retrieval import RetrieveRequest, RetrieveResponse
from app.services.retrieval import retrieve_policy

logger = structlog.get_logger()


async def answer_policy(request: RetrieveRequest, settings: Settings) -> AnswerResponse:
    async def retrieve(value: RetrieveRequest) -> RetrieveResponse:
        return await retrieve_policy(value, settings)

    chain = build_answer_chain(RunnableLambda(retrieve), get_chat_model(settings), settings)
    with LLMObs.workflow(name="policy_answer") if LLMObs.enabled else nullcontext() as span:
        response = await chain.ainvoke(request)
        if span is not None:
            try:
                LLMObs.annotate(
                    span=span,
                    input_data=request.model_dump(mode="json"),
                    output_data=response.model_dump(mode="json"),
                )
                exported = LLMObs.export_span(span)
                if exported is not None:
                    response.datadog_span_id = exported["span_id"]
            except Exception as exc:  # noqa: BLE001 - optional telemetry must preserve the answer
                logger.warning("answer_datadog_publish_failed", error_type=type(exc).__name__)
    logger.info(
        "answer_completed",
        status=response.status,
        citation_count=len(response.citations),
        generation_ms=response.generation_ms,
    )
    return response
