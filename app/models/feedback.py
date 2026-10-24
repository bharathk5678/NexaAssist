from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.answer import AnswerResponse
from app.models.retrieval import RetrieveRequest


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: RetrieveRequest
    response: AnswerResponse
    helpful: bool
    submitter_id: UUID = Field(default_factory=uuid4)
    submission_id: UUID = Field(default_factory=uuid4)
    correction: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def matching_dates(self) -> FeedbackRequest:
        if self.request.as_of != self.response.as_of:
            raise ValueError("Feedback request and response must have the same as_of date")
        return self


class FeedbackRecord(FeedbackRequest):
    feedback_id: UUID
    created_at: datetime
    status: Literal["pending", "accepted", "rejected"] = "pending"
    reviewer: str | None = None
    review_note: str = ""


class FeedbackReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal["accepted", "rejected"]
    reviewer: str = Field(min_length=1, max_length=100)
    review_note: str = Field(min_length=1, max_length=4000)
