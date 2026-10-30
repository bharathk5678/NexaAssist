"""Define durable run views, reviewer decisions and canonical approval fingerprints."""

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
    """Validated approval decision contract.

    Attributes:
        decision: Reviewer decision bound to the exact retained proposal hash.
        proposal_hash: Canonical fingerprint binding request, proposal and retained evidence.
    """

    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    proposal_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class AgentRunResponse(BaseModel):
    """Validated agent run response contract.

    Attributes:
        run_id: Identifier of the saved workflow to read or resume.
        status: HTTP or workflow status used by the scenario.
        created_at: Timezone-aware creation timestamp of the saved run or receipt.
        expires_at: Timestamp after which a pending proposal can no longer be approved.
        proposal_hash: Canonical fingerprint binding request, proposal and retained evidence.
        response: Validated answer or workflow result retained for rendering.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    status: AgentStatus | Literal["running", "pending_approval", "expired", "unconfirmed", "failed"]
    created_at: datetime
    expires_at: datetime
    proposal_hash: str | None = None
    response: AgentResponse | None = None


def proposal_digest(request: AgentRequest, validation: ValidationResult) -> str:
    """Bind approval to the exact request, proposal and retained policy evidence.

    Args:
        request: Validated request retaining the caller's explicit scope and action details.
        validation: Retained policy and banking validation for the exact proposed action.

    Returns:
        Canonical SHA-256 fingerprint binding request, proposal and retained evidence.
    """
    body = {
        "request": request.model_dump(mode="json"),
        "validation": validation.model_dump(mode="json"),
    }
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
