"""Define structured drafts, exact evidence quotes and cited answer responses."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.retrieval import Citation, RetrieveTimings


class EvidenceQuote(BaseModel):
    """Validated evidence quote contract.

    Attributes:
        evidence_id: Number joining an inline answer marker to its retained source.
        quote: Exact contiguous evidence text supporting the cited answer.
    """

    model_config = ConfigDict(extra="forbid")

    evidence_id: int = Field(ge=1)
    quote: str = Field(min_length=1)


class AnswerDraft(BaseModel):
    """Model output; source identities are resolved by application code.

    Attributes:
        status: HTTP or workflow status used by the scenario.
        answer: Generated answer whose exact text and citations are being evaluated.
        evidence: Retained retrieval results and complete applicable amendments.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["answered", "insufficient_evidence", "needs_clarification"]
    answer: str = Field(min_length=1)
    evidence: list[EvidenceQuote]


class AnswerCitation(EvidenceQuote):
    # The quote can come from another clause in the matched child's parent section.
    """Answer Citation used by answer.

    Attributes:
        matched_child: Scoped child citation associated with the quoted retained passage.
    """

    matched_child: Citation


class AnswerResponse(BaseModel):
    """Validated answer response contract.

    Attributes:
        as_of: Policy lookup date; not the customer loan sanction date.
        status: HTTP or workflow status used by the scenario.
        answer: Generated answer whose exact text and citations are being evaluated.
        citations: Verified evidence references and exact quotes accompanying the answer.
        retrieval_timings: Search, parent-expansion and total retrieval durations.
        generation_ms: Elapsed answer-generation time in milliseconds.
        datadog_span_id: Exported workflow span identity used to join feedback/evaluations.
    """

    model_config = ConfigDict(extra="forbid")

    as_of: date
    status: Literal["answered", "insufficient_evidence", "needs_clarification"]
    answer: str
    citations: list[AnswerCitation]
    retrieval_timings: RetrieveTimings
    generation_ms: float
    datadog_span_id: str | None = Field(default=None, pattern=r"^[1-9][0-9]{0,19}$")
