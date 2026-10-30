"""Retrieve policy evidence over the existing RAG HTTP contract."""

from __future__ import annotations

import httpx

from app.models.retrieval import RetrieveRequest, RetrieveResponse


async def retrieve_over_http(
    request: RetrieveRequest, client: httpx.AsyncClient
) -> RetrieveResponse:
    """Use the unchanged Phase 1 contract, including complete amendments.

    Args:
        request: Validated request retaining the caller's explicit scope and action details.
        client: HTTP client configured for the required upstream service.

    Returns:
        Validated policy evidence matching the requested date.

    Raises:
        ValueError: Retrieval response date differs from requested scope.
        httpx.HTTPStatusError: The RAG service returns an unsuccessful status.
        ValidationError: The response does not match the retrieval contract.
    """
    response = await client.post("retrieve", json=request.model_dump(mode="json"))
    response.raise_for_status()
    retrieved = RetrieveResponse.model_validate_json(response.content, strict=True)
    if retrieved.as_of != request.as_of:
        raise ValueError("Retrieval response date differs from requested scope")
    return retrieved
