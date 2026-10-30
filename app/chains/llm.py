"""Construct the configured chat integration with bounded calls and token logging."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.core.observability import TokenUsageLogger


def get_chat_model(settings: Settings) -> ChatOpenAI:
    """Construct the configured Responses API chat model with bounded retries.

    Args:
        settings: Validated application configuration for this operation.

    Returns:
        Configured ChatOpenAI integration used by classification and generation.
    """
    return ChatOpenAI(
        model=settings.chat_model,
        api_key=settings.openai_api_key,
        use_responses_api=True,
        timeout=60,
        max_retries=1,
        max_completion_tokens=settings.chat_max_output_tokens,
        callbacks=[TokenUsageLogger()],
    )
