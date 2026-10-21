"""Evaluation contracts and mechanical checks; these do not score semantic truth."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.chains.answer import INSUFFICIENT_EVIDENCE
from app.models.answer import AnswerResponse
from app.models.retrieval import RetrieveHit, RetrieveRequest, RetrieveResponse


class ExpectedEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(min_length=1)
    clause: str | None = None
    clause_key: str | None = None


class GoldenAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: RetrieveRequest
    expected_output: str = Field(min_length=1)
    context: list[ExpectedEvidence]
    expected_status: Literal["answered", "insufficient_evidence"]


class EvidenceContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: int = Field(ge=1)
    hit: RetrieveHit


class EvaluationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    golden: GoldenAnswer
    response: AnswerResponse
    sources: list[EvidenceContext]


def load_golden(path: Path) -> list[GoldenAnswer]:
    cases = [
        GoldenAnswer.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    if not cases:
        raise ValueError("Golden dataset is empty")
    return cases


def capture_sources(retrieved: RetrieveResponse) -> list[EvidenceContext]:
    """Mirror the answer chain's document/version/parent deduplication, in order."""
    # shortcut: keep this key aligned with build_answer_chain until it exposes context.
    unique: dict[tuple[str, str, str], RetrieveHit] = {}
    for hit in retrieved.results:
        key = (hit.citation.doc_id, hit.citation.policy_version, hit.parent_text)
        unique.setdefault(key, hit)
    return [EvidenceContext(evidence_id=i, hit=hit) for i, hit in enumerate(unique.values(), 1)]


def mechanical_checks(record: EvaluationRecord) -> dict[str, bool | float | None]:
    """Citation identity/quote checks and child-ID coverage, never semantic recall."""
    response, expected = record.response, record.golden
    sources = {source.evidence_id: source.hit for source in record.sources}
    markers = {int(number) for number in re.findall(r"\[(\d+)\]", response.answer)}
    ids = {citation.evidence_id for citation in response.citations}
    if response.status == "insufficient_evidence":
        valid = not response.citations and not markers and response.answer == INSUFFICIENT_EVIDENCE
    else:
        valid = (
            bool(ids)
            and markers == ids
            and all(
                citation.evidence_id in sources
                and bool(citation.quote.strip())
                and citation.quote in sources[citation.evidence_id].parent_text
                and citation.matched_child == sources[citation.evidence_id].citation
                for citation in response.citations
            )
        )
    covered = sum(
        any(
            source.hit.citation.doc_id == ref.doc_id
            and (ref.clause is None or source.hit.citation.clause == ref.clause)
            for source in record.sources
        )
        for ref in expected.context
    )
    return {
        "status_matches": response.status == expected.expected_status,
        "citation_integrity": valid,
        "child_reference_coverage": covered / len(expected.context) if expected.context else None,
    }
