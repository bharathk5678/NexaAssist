from __future__ import annotations

from collections import deque
from math import ceil
from typing import Any

import structlog
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult

retrieval_latencies: deque[float] = deque(maxlen=1000)


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
