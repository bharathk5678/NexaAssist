"""Define feedback submissions and reviewer-owned decision records."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.answer import AnswerResponse
from app.models.retrieval import RetrieveRequest


class FeedbackRequest(BaseModel):
    """Validated feedback request contract.

    Attributes:
        request: Validated request retaining the caller's explicit scope and action details.
        response: Validated answer or workflow result retained for rendering.
        helpful: User assessment of whether the retained answer was helpful.
        submitter_id: Local submitter identity used to scope feedback idempotency.
        submission_id: Caller-supplied idempotent feedback submission identifier.
        correction: Optional user-supplied correction or missing policy evidence.
    """

    model_config = ConfigDict(extra="forbid")

    request: RetrieveRequest
    response: AnswerResponse
    helpful: bool
    submitter_id: UUID = Field(default_factory=uuid4)
    submission_id: UUID = Field(default_factory=uuid4)
    correction: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def matching_dates(self) -> FeedbackRequest:
        """Require feedback request and answer policy dates to agree.

        Returns:
            FeedbackRequest value produced by this operation.

        Raises:
            ValueError: Feedback request and response must have the same as_of date.
        """
        if self.request.as_of != self.response.as_of:
            raise ValueError("Feedback request and response must have the same as_of date")
        return self


class FeedbackRecord(FeedbackRequest):
    """Feedback Record used by feedback.

    Attributes:
        feedback_id: Stable identifier of the saved feedback record.
        created_at: Timezone-aware creation timestamp of the saved run or receipt.
        status: HTTP or workflow status used by the scenario.
        reviewer: Named feedback reviewer recorded with the decision.
        review_note: Reviewer explanation accompanying the feedback decision.
    """

    feedback_id: UUID
    created_at: datetime
    status: Literal["pending", "accepted", "rejected"] = "pending"
    reviewer: str | None = None
    review_note: str = ""


class FeedbackReview(BaseModel):
    """Validated feedback review contract.

    Attributes:
        status: HTTP or workflow status used by the scenario.
        reviewer: Named feedback reviewer recorded with the decision.
        review_note: Reviewer explanation accompanying the feedback decision.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal["accepted", "rejected"]
    reviewer: str = Field(min_length=1, max_length=100)
    review_note: str = Field(min_length=1, max_length=4000)
