from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.agent import AgentRequest, AgentResponse, AgentStatus
from app.models.validation import ValidationResult


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    proposal_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    status: AgentStatus | Literal["running", "pending_approval", "expired", "unconfirmed", "failed"]
    created_at: datetime
    expires_at: datetime
    proposal_hash: str | None = None
    response: AgentResponse | None = None


def proposal_digest(request: AgentRequest, validation: ValidationResult) -> str:
    """Bind approval to the exact request, proposal and retained policy evidence."""
    body = {
        "request": request.model_dump(mode="json"),
        "validation": validation.model_dump(mode="json"),
    }
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
