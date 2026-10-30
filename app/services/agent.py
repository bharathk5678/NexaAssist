from __future__ import annotations

import asyncio
import json
from collections import Counter
from collections.abc import Awaitable, Callable
from contextlib import nullcontext

import httpx
import structlog
from ddtrace.llmobs import LLMObs
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from app.agents.orchestrator import build_agent_graph
from app.chains.answer import build_answer_chain
from app.chains.llm import get_chat_model
from app.chains.prompts.orchestrator import (
    ORCHESTRATOR_PROMPT,
    ORCHESTRATOR_PROMPT_ID,
    ORCHESTRATOR_PROMPT_VERSION,
)
from app.core.agent_budget import AgentModelBudget
from app.core.config import AgentSettings, Settings
from app.core.observability import prompt_annotation_context
from app.models.agent import AgentRequest, AgentResponse, IntentDecision
from app.models.answer import AnswerResponse
from app.models.retrieval import RetrieveRequest, RetrieveResponse
from app.models.validation import SubmittedServiceRequest, ValidationAccess, ValidationResult
from app.services.agent_retrieval import retrieve_over_http
from app.services.validation import validate_service_request

logger = structlog.get_logger()
agent_metrics: Counter[str] = Counter()


def build_workflow(
    settings: Settings,
    client: httpx.AsyncClient,
    *,
    access: ValidationAccess | None = None,
    banking_client: httpx.AsyncClient | None = None,
    agent_settings: AgentSettings | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
    actioner: Callable[[AgentRequest, ValidationResult, str], Awaitable[SubmittedServiceRequest]]
    | None = None,
) -> CompiledStateGraph:
    model_settings = (
        settings.model_copy(
            update={"chat_max_output_tokens": agent_settings.agent_model_max_output_tokens}
        )
        if agent_settings is not None
        else settings
    )
    llm = get_chat_model(model_settings)
    budget = (
        AgentModelBudget(agent_settings, settings.token_encoding)
        if agent_settings is not None
        else None
    )
    callbacks: list[BaseCallbackHandler] = [budget] if budget is not None else []
    classification = ORCHESTRATOR_PROMPT | llm.with_structured_output(
        IntentDecision, method="json_schema", strict=True
    )

    async def classify(value: AgentRequest) -> IntentDecision:
        # Notes belong to the fixed bank payload, not to the routing model.
        routing_request = value.model_dump(mode="json")
        if routing_request["action_details"] is not None:
            routing_request["action_details"].pop("notes", None)
        variables = {"request": json.dumps(routing_request)}
        with prompt_annotation_context(
            ORCHESTRATOR_PROMPT,
            variables,
            prompt_id=ORCHESTRATOR_PROMPT_ID,
            version=ORCHESTRATOR_PROMPT_VERSION,
        ):
            return IntentDecision.model_validate(
                await classification.ainvoke(variables, config={"callbacks": callbacks})
            )

    async def retrieve(value: RetrieveRequest) -> RetrieveResponse:
        return await retrieve_over_http(value, client)

    async def answer(value: RetrieveRequest, evidence: RetrieveResponse) -> AnswerResponse:
        chain = build_answer_chain(RunnableLambda(lambda _: evidence), llm, settings)
        return await chain.ainvoke(value, config={"callbacks": callbacks})

    async def validate(value: AgentRequest, evidence: RetrieveResponse) -> ValidationResult:
        assert banking_client is not None and access is not None
        with (
            LLMObs.workflow(
                name=(
                    "validator_opt_in"
                    if value.action_details is not None
                    and value.action_details.request_type == "OPT_IN_CIR_2026_07_PART_PREPAY"
                    else "validator_service_request"
                ),
                agent_service=settings.dd_service,
            )
            if LLMObs.enabled
            else nullcontext()
        ):
            result = await validate_service_request(value, evidence, banking_client, access)
        logger.info("agent_validation_completed", decision=result.decision)
        return result

    return build_agent_graph(
        RunnableLambda(classify),
        RunnableLambda(retrieve),
        answer,
        validator=validate if banking_client is not None else None,
        access=access,
        checkpointer=checkpointer,
        actioner=actioner,
    )


async def orchestrate(
    request: AgentRequest,
    settings: Settings,
    agent_settings: AgentSettings,
    client: httpx.AsyncClient,
    *,
    access: ValidationAccess | None = None,
    banking_client: httpx.AsyncClient | None = None,
) -> AgentResponse:
    agent_metrics["requests"] += 1
    graph = build_workflow(
        settings,
        client,
        access=access,
        banking_client=banking_client,
        agent_settings=agent_settings,
    )
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
