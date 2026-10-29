from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.retrieval import Citation, RetrieveTimings


class EvidenceQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: int = Field(ge=1)
    quote: str = Field(min_length=1)


class AnswerDraft(BaseModel):
    """Model output; source identities are resolved by application code."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["answered", "insufficient_evidence", "needs_clarification"]
    answer: str = Field(min_length=1)
    evidence: list[EvidenceQuote]


class AnswerCitation(EvidenceQuote):
    # The quote can come from another clause in the matched child's parent section.
    matched_child: Citation


class AnswerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: date
    status: Literal["answered", "insufficient_evidence", "needs_clarification"]
    answer: str
    citations: list[AnswerCitation]
    retrieval_timings: RetrieveTimings
    generation_ms: float
    datadog_span_id: str | None = Field(default=None, pattern=r"^[1-9][0-9]{0,19}$")
