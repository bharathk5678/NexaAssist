from __future__ import annotations

import asyncio
from collections import Counter
from contextlib import nullcontext

import httpx
import structlog
from ddtrace.llmobs import LLMObs
from langchain_core.runnables import RunnableLambda

from app.agents.orchestrator import build_agent_graph
from app.chains.answer import build_answer_chain
from app.chains.llm import get_chat_model
from app.chains.prompts.orchestrator import (
    ORCHESTRATOR_PROMPT,
    ORCHESTRATOR_PROMPT_ID,
    ORCHESTRATOR_PROMPT_VERSION,
)
from app.core.config import AgentSettings, Settings
from app.core.observability import prompt_annotation_context
from app.models.agent import AgentRequest, AgentResponse, IntentDecision
from app.models.answer import AnswerResponse
from app.models.retrieval import RetrieveRequest, RetrieveResponse
from app.services.agent_retrieval import retrieve_over_http

logger = structlog.get_logger()
agent_metrics: Counter[str] = Counter()


async def orchestrate(
    request: AgentRequest,
    settings: Settings,
    agent_settings: AgentSettings,
    client: httpx.AsyncClient,
) -> AgentResponse:
    agent_metrics["requests"] += 1
    llm = get_chat_model(settings)
    classification = ORCHESTRATOR_PROMPT | llm.with_structured_output(
        IntentDecision, method="json_schema", strict=True
    )

    async def classify(value: AgentRequest) -> IntentDecision:
        variables = {"request": value.model_dump_json()}
        with prompt_annotation_context(
            ORCHESTRATOR_PROMPT,
            variables,
            prompt_id=ORCHESTRATOR_PROMPT_ID,
            version=ORCHESTRATOR_PROMPT_VERSION,
        ):
            return IntentDecision.model_validate(await classification.ainvoke(variables))

    async def retrieve(value: RetrieveRequest) -> RetrieveResponse:
        return await retrieve_over_http(value, client)

    async def answer(value: RetrieveRequest, evidence: RetrieveResponse) -> AnswerResponse:
        chain = build_answer_chain(RunnableLambda(lambda _: evidence), llm, settings)
        return await chain.ainvoke(value)

    graph = build_agent_graph(RunnableLambda(classify), RunnableLambda(retrieve), answer)
    with (
        LLMObs.workflow(name="agent_orchestration", agent_service=settings.dd_service)
        if LLMObs.enabled
        else nullcontext()
    ):
        async with asyncio.timeout(agent_settings.agent_run_timeout_seconds):
            state = await graph.ainvoke({"request": request}, config={"recursion_limit": 8})
    response = AgentResponse.model_validate(state["response"])
    agent_metrics["completed"] += 1
    logger.info("agent_completed", intent=response.intent, status=response.status)
    return response
