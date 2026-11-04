"""Provide bounded RAG and authenticated banking HTTP clients to both agent routers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import Depends

from app.core.config import AgentSettings, get_agent_settings


async def rag_client(
    settings: Annotated[AgentSettings, Depends(get_agent_settings)],
) -> AsyncIterator[httpx.AsyncClient]:
    """Yield a bounded HTTP client targeting the policy retrieval service.

    Yields:
        Bounded RAG HTTP client closed when the request dependency exits.
    """
    async with httpx.AsyncClient(
        base_url=str(settings.rag_base_url).rstrip("/") + "/",
        timeout=settings.agent_http_timeout_seconds,
        follow_redirects=False,
    ) as client:
        yield client


async def banking_client(
    settings: Annotated[AgentSettings, Depends(get_agent_settings)],
) -> AsyncIterator[httpx.AsyncClient | None]:
    """Yield an authenticated bounded banking client, or None when unconfigured.

    Yields:
        Authenticated banking HTTP client, or None when unconfigured.
    """
    if settings.banking_api_token is None:
        yield None
        return
    async with httpx.AsyncClient(
        base_url=str(settings.banking_base_url).rstrip("/") + "/",
        headers={"Authorization": "Bearer " + settings.banking_api_token.get_secret_value()},
        timeout=settings.agent_http_timeout_seconds,
        follow_redirects=False,
    ) as client:
        yield client
