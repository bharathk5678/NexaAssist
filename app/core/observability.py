from __future__ import annotations

from collections import deque
from contextlib import AbstractContextManager, nullcontext
from math import ceil
from typing import Any

import structlog
from ddtrace.llmobs import LLMObs
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult
from langchain_core.prompts import ChatPromptTemplate

retrieval_latencies: deque[float] = deque(maxlen=1000)


def prompt_annotation_context(
    prompt: ChatPromptTemplate,
    variables: dict[str, str],
    *,
    prompt_id: str,
    version: str,
) -> AbstractContextManager[None]:
    """Track the existing text prompt without maintaining a second template."""
    if not LLMObs.enabled:
        return nullcontext()
    messages = prompt.format_messages(
        **{name: "{{" + name + "}}" for name in prompt.input_variables}
    )
    return LLMObs.annotation_context(
        prompt={
            "id": prompt_id,
            "version": version,
            "chat_template": [
                {
                    "role": {"human": "user", "ai": "assistant"}.get(message.type, message.type),
                    "content": message.content,
                }
                for message in messages
            ],
            "variables": variables,
        }
    )


def latency_summary() -> dict[str, int | float]:
    values = sorted(retrieval_latencies)
    result: dict[str, int | float] = {"sample_count": len(values)}
    for label, fraction in (("p50_ms", 0.5), ("p95_ms", 0.95), ("p99_ms", 0.99)):
        result[label] = values[max(0, ceil(fraction * len(values)) - 1)] if values else 0
    return result


class TokenUsageLogger(AsyncCallbackHandler):
    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        for generations in response.generations:
            for generation in generations:
                message = getattr(generation, "message", None)
                if isinstance(message, AIMessage) and message.usage_metadata:
                    structlog.get_logger().info("model_token_usage", **message.usage_metadata)
