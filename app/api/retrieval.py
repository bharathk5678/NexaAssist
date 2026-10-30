"""Expose scoped policy retrieval with safe HTTP error responses."""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.models.retrieval import RetrieveRequest, RetrieveResponse
from app.services.retrieval import retrieve_policy

router = APIRouter()
logger = structlog.get_logger()


@router.post("/retrieve")
async def retrieve(
    request: RetrieveRequest, settings: Annotated[Settings, Depends(get_settings)]
) -> RetrieveResponse:
    """Serve policy retrieval and translate upstream failures into a safe HTTP response.

    Args:
        request: Validated request retaining the caller's explicit scope and action details.
        settings: Validated application configuration for this operation.

    Returns:
        RetrieveResponse value produced by this operation.

    Raises:
        HTTPException: Retrieval service unavailable.
    """
    try:
        return await retrieve_policy(request, settings)
    except Exception:
        logger.exception("retrieval_failed")
        raise HTTPException(status_code=503, detail="Retrieval service unavailable") from None
