"""Define scoped retrieval requests, ranked evidence and timing responses."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class RetrieveRequest(BaseModel):
    """Validated retrieve request contract.

    Attributes:
        query: User question or scoped retrieval query.
        as_of: Policy lookup date; not the customer loan sanction date.
        top_k: Maximum number of ranked primary sources requested.
        product_id: Explicit product scope, when required or supplied.
        jurisdiction: Jurisdiction boundary retained in the policy lookup scope.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=2000)
    as_of: date
    top_k: int = Field(default=5, ge=1, le=20)
    product_id: str | None = Field(default=None, min_length=1)
    jurisdiction: str | None = Field(default=None, min_length=1)


class Citation(BaseModel):
    """Validated citation contract.

    Attributes:
        doc_id: Stable policy instrument identifier across stored records.
        title: Published policy or instrument title retained in citations.
        policy_version: Published version of the cited policy instrument.
        clause: Published clause identifier, or None for complete instruments/front matter.
        effective_date: First policy date on which the document/version applies.
    """

    model_config = ConfigDict(extra="forbid")

    doc_id: str
    title: str
    policy_version: str
    clause: str | None
    effective_date: date


class RetrieveHit(BaseModel):
    """Validated retrieve hit contract.

    Attributes:
        rank: One-based position of the retained search result.
        score: Search/reranker relevance score supplied with the retained hit.
        text: Retained source passage or bounded note content.
        parent_text: Complete retained parent or child passage supplied as evidence.
        citation: Document version, clause and effective date identifying this evidence.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    rank: int
    score: float
    text: str
    parent_text: str
    citation: Citation


class RetrieveTimings(BaseModel):
    """Validated retrieve timings contract.

    Attributes:
        search_ms: Elapsed candidate-search time in milliseconds.
        parent_ms: Elapsed parent-expansion time in milliseconds.
        total_ms: Total retrieval duration in milliseconds.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    search_ms: float
    parent_ms: float
    total_ms: float


class RetrieveResponse(BaseModel):
    """Validated retrieve response contract.

    Attributes:
        as_of: Policy lookup date; not the customer loan sanction date.
        results: Ranked scoped retrieval hits before complete-amendment deduplication.
        timings: Measured candidate search, parent expansion and total retrieval times.
        amendments: Complete applicable amendment instruments retained alongside ranked results.
    """

    model_config = ConfigDict(extra="forbid")

    as_of: date
    results: list[RetrieveHit]
    timings: RetrieveTimings
    amendments: list[RetrieveHit] = Field(default_factory=list)

    @property
    def evidence(self) -> list[RetrieveHit]:
        """Combine complete amendments and results without duplicating document versions.

        Returns:
            Ordered results produced by the documented operation.
        """
        complete = {(hit.citation.doc_id, hit.citation.policy_version) for hit in self.amendments}
        return self.amendments + [
            hit
            for hit in self.results
            if (hit.citation.doc_id, hit.citation.policy_version) not in complete
        ]
