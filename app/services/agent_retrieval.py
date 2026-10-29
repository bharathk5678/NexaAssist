from __future__ import annotations

import httpx

from app.models.retrieval import RetrieveRequest, RetrieveResponse


async def retrieve_over_http(
    request: RetrieveRequest, client: httpx.AsyncClient
) -> RetrieveResponse:
    """Use the unchanged Phase 1 contract, including complete amendments."""
    response = await client.post("retrieve", json=request.model_dump(mode="json"))
    response.raise_for_status()
    retrieved = RetrieveResponse.model_validate_json(response.content, strict=True)
    if retrieved.as_of != request.as_of:
        raise ValueError("Retrieval response date differs from requested scope")
    return retrieved
