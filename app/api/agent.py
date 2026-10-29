from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException
from langchain_core.exceptions import OutputParserException
from langchain_openai.chat_models.base import OpenAIRefusalError
from openai import OpenAIError

from app.api.operations import health
from app.core.config import AgentSettings, Settings, get_agent_settings, get_settings
from app.models.agent import AgentRequest, AgentResponse
from app.services.agent import agent_metrics, orchestrate

router = APIRouter()
logger = structlog.get_logger()
router.add_api_route("/health", health, methods=["GET"])


@router.get("/metrics")
async def metrics() -> dict[str, int]:
    return {
        "agent_requests_total": agent_metrics["requests"],
        "agent_completed_total": agent_metrics["completed"],
    }


async def rag_client(
    settings: Annotated[AgentSettings, Depends(get_agent_settings)],
) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        base_url=str(settings.rag_base_url).rstrip("/") + "/",
        timeout=settings.agent_http_timeout_seconds,
        follow_redirects=False,
    ) as client:
        yield client


@router.post("/agent", response_model=AgentResponse)
async def agent(
    request: AgentRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    agent_settings: Annotated[AgentSettings, Depends(get_agent_settings)],
    client: Annotated[httpx.AsyncClient, Depends(rag_client)],
) -> AgentResponse:
    try:
        return await orchestrate(request, settings, agent_settings, client)
    except (
        httpx.HTTPError,
        OpenAIError,
        OpenAIRefusalError,
        OutputParserException,
        ValueError,
        TimeoutError,
    ) as exc:
        logger.error("agent_failed", error_type=type(exc).__name__)
        raise HTTPException(status_code=503, detail="Agent service unavailable") from None
