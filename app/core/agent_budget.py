from __future__ import annotations

import json
from typing import Any

import structlog
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage

from app.chains.context import token_encoder
from app.core.config import AgentSettings


class AgentModelBudget(AsyncCallbackHandler):
    """Reserve bounded model work before calls, including one possible provider retry."""

    raise_error = True

    def __init__(self, settings: AgentSettings, encoding: str) -> None:
        self.settings = settings
        self.encoder = token_encoder(encoding)
        self.calls = 0
        self.reserved_tokens = 0

    async def on_chat_model_start(
        self, serialized: dict[str, Any], messages: list[list[BaseMessage]], **kwargs: Any
    ) -> None:
        payload = {
            "messages": [[m.model_dump(mode="json") for m in batch] for batch in messages],
            "parameters": kwargs.get("invocation_params", {}),
        }
        prompt_tokens = len(
            self.encoder.encode(json.dumps(payload, default=str), disallowed_special=())
        )
        # This is a conservative local estimate, not provider billing or a dollar-cost claim.
        reservation = 2 * (
            prompt_tokens + len(messages) * self.settings.agent_model_max_output_tokens
        )
        if (
            self.calls + len(messages) > self.settings.agent_model_max_calls
            or self.reserved_tokens + reservation > self.settings.agent_model_token_budget
        ):
            raise ValueError("Agent model-work budget exceeded")
        self.calls += len(messages)
        self.reserved_tokens += reservation
        structlog.get_logger().info(
            "agent_model_budget", calls=self.calls, reserved_tokens=self.reserved_tokens
        )
