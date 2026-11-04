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
    """Validated expected evidence contract.

    Attributes:
        doc_id: Stable policy instrument identifier across stored records.
        clause: Published clause identifier, or None for complete instruments/front matter.
        clause_key: Optional metadata key resolving the expected clause evidence.
    """

    model_config = ConfigDict(extra="forbid")

    doc_id: str = Field(min_length=1)
    clause: str | None = None
    clause_key: str | None = None


class GoldenAnswer(BaseModel):
    """Validated golden answer contract.

    Attributes:
        input: Validated scoped policy request for the evaluation case.
        expected_output: Reference answer for the golden evaluation case.
        context: Expected policy evidence references for a golden evaluation case.
        expected_status: Required answer/abstention/clarification outcome for the case.
    """

    model_config = ConfigDict(extra="forbid")

    input: RetrieveRequest
    expected_output: str = Field(min_length=1)
    context: list[ExpectedEvidence]
    expected_status: Literal["answered", "insufficient_evidence", "needs_clarification"]


class EvidenceContext(BaseModel):
    """Validated evidence context contract.

    Attributes:
        evidence_id: Number joining an inline answer marker to its retained source.
        hit: Retained retrieved passage and its source citation.
    """

    model_config = ConfigDict(extra="forbid")

    evidence_id: int = Field(ge=1)
    hit: RetrieveHit


class EvaluationRecord(BaseModel):
    """Validated evaluation record contract.

    Attributes:
        case_id: Identifier linking a diagnostic or request to its retained case.
        golden: Expected case contract used for the diagnostic.
        response: Validated answer or workflow result retained for rendering.
        sources: Numbered policy passages and citation metadata retained for generation.
    """

    model_config = ConfigDict(extra="forbid")

    case_id: str
    golden: GoldenAnswer
    response: AnswerResponse
    sources: list[EvidenceContext]


def load_golden(path: Path) -> list[GoldenAnswer]:
    """Load and validate the mechanical-check golden dataset, rejecting an empty file.

    Returns:
        Nonempty sequence of validated mechanical-check golden cases.

    Raises:
        ValueError: Golden dataset is empty.
    """
    cases = [
        GoldenAnswer.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    if not cases:
        raise ValueError("Golden dataset is empty")
    return cases


def capture_sources(retrieved: RetrieveResponse) -> list[EvidenceContext]:
    """Mirror the answer chain's document/version/parent deduplication, in order.

    Returns:
        Ordered unique evidence identities for mechanical fixture checks.
    """
    # shortcut: keep this key aligned with build_answer_chain until it exposes context.
    unique: dict[tuple[str, str, str], RetrieveHit] = {}
    for hit in retrieved.evidence:
        key = (hit.citation.doc_id, hit.citation.policy_version, hit.parent_text)
        unique.setdefault(key, hit)
    return [EvidenceContext(evidence_id=i, hit=hit) for i, hit in enumerate(unique.values(), 1)]


def mechanical_checks(record: EvaluationRecord) -> dict[str, bool | float | None]:
    """Citation identity/quote checks and child-ID coverage, never semantic recall.

    Args:
        record: Retained evaluation case, generated answer and supporting source identities.

    Returns:
        Status, exact-citation and child-reference-coverage results.
    """
    response, expected = record.response, record.golden
    sources = {source.evidence_id: source.hit for source in record.sources}
    markers = {int(number) for number in re.findall(r"\[(\d+)\]", response.answer)}
    ids = {citation.evidence_id for citation in response.citations}
    if response.status == "insufficient_evidence":
        valid = not response.citations and not markers and response.answer == INSUFFICIENT_EVIDENCE
    elif response.status == "needs_clarification":
        valid = not response.citations and not markers and response.answer.rstrip().endswith("?")
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
