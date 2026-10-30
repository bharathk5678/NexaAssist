"""Construct the shared embedding integration for ingestion and retrieval."""

from __future__ import annotations

from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings


def get_embeddings(settings: Settings) -> OpenAIEmbeddings:
    """Ingestion and retrieval must share this model and dimension.

    Args:
        settings: Validated application configuration for this operation.

    Returns:
        Configured OpenAIEmbeddings integration with the shared model and dimensions.
    """
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        chunk_size=settings.embedding_batch_size,
        openai_api_key=settings.openai_api_key,
    )
