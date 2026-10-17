from __future__ import annotations

import structlog
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

    chain = build_answer_chain(RunnableLambda(retrieve), get_chat_model(settings))
    response = await chain.ainvoke(request)
    logger.info(
        "answer_completed",
        status=response.status,
        citation_count=len(response.citations),
        generation_ms=response.generation_ms,
    )
    return response
