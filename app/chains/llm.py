from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import Settings


def get_chat_model(settings: Settings) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.chat_model,
        api_key=settings.openai_api_key,
        use_responses_api=True,
        timeout=60,
        max_retries=1,
    )
