from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.answer import AnswerResponse

Intent = Literal[
    "policy_question", "missing_information", "forbidden", "customer_context", "supported_action"
]
Action = Literal["createCase", "addCaseNote", "escalateCase", "createServiceRequest"]
MissingField = Literal["product_id", "as_of", "customer_id", "action", "action_details", "question"]


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=2000)
    as_of: date | None = None
    product_id: str | None = Field(default=None, min_length=1)
    customer_id: str | None = Field(default=None, pattern=r"^NXC-[0-9]{4}$")
    action: Action | None = None
    jurisdiction: str | None = Field(default=None, min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class IntentDecision(BaseModel):
    """Structured model output; extracted values must be explicit in the request."""

    model_config = ConfigDict(extra="forbid")

    intent: Intent
    product_id: str | None
    as_of: date | None
    customer_id: str | None = Field(pattern=r"^NXC-[0-9]{4}$")
    action: Action | None
    product_required: bool
    missing_fields: list[MissingField]


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    status: Literal[
        "answered", "insufficient_evidence", "needs_clarification", "forbidden", "unavailable"
    ]
    message: str
    missing_fields: list[MissingField] = Field(default_factory=list)
    answer: AnswerResponse | None = None
