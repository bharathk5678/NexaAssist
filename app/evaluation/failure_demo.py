"""Controlled fixtures using repository policy facts, never live Atlas observations."""

from __future__ import annotations

from pathlib import Path

from app.chains.answer import INSUFFICIENT_EVIDENCE
from app.evaluation.answer_evaluation import (
    EvaluationRecord,
    capture_sources,
    load_golden,
    mechanical_checks,
)
from app.models.answer import AnswerCitation, AnswerResponse
from app.models.retrieval import Citation, RetrieveHit, RetrieveResponse, RetrieveTimings


def demo_report(dataset: Path) -> dict[str, object]:
    cases = load_golden(dataset)
    golden = cases[0]
    quote = "Maximum loan amount: ₹7.5 crore."
    citation = Citation(
        doc_id="POL-HL-V3",
        title="NexaHome Loan Policy",
        policy_version="3.0",
        clause="4.1",
        effective_date="2025-10-01",
    )
    timings = RetrieveTimings(search_ms=0, parent_ms=0, total_ms=0)
    retrieved = RetrieveResponse(
        as_of=golden.input.as_of,
        timings=timings,
        results=[RetrieveHit(rank=1, score=1, text=quote, parent_text=quote, citation=citation)],
    )
    response = AnswerResponse(
        as_of=golden.input.as_of,
        status="answered",
        answer="The maximum is ₹7.5 crore [1].",
        citations=[AnswerCitation(evidence_id=1, quote=quote, matched_child=citation)],
        retrieval_timings=timings,
        generation_ms=0,
    )
    base = EvaluationRecord(
        case_id="valid_reference",
        golden=golden,
        response=response,
        sources=capture_sources(retrieved),
    )
    wrong_claim = base.model_copy(
        update={
            "case_id": "wrong_amount_real_quote",
            "response": response.model_copy(update={"answer": "The maximum is ₹9 crore [1]."}),
        }
    )
    bad_quote = base.model_copy(
        update={
            "case_id": "invented_quote",
            "response": response.model_copy(
                update={
                    "citations": [
                        response.citations[0].model_copy(
                            update={"quote": "Maximum loan amount: ₹9 crore."}
                        )
                    ]
                }
            ),
        }
    )
    missing_circular = base.model_copy(
        update={
            "case_id": "required_circular_missing",
            "golden": cases[1],
        }
    )
    abstention = base.model_copy(
        update={
            "case_id": "correct_abstention",
            "golden": cases[8],
            "sources": [],
            "response": response.model_copy(
                update={
                    "status": "insufficient_evidence",
                    "answer": INSUFFICIENT_EVIDENCE,
                    "citations": [],
                }
            ),
        }
    )
    records = [base, wrong_claim, bad_quote, missing_circular, abstention]
    rows = [{"case_id": row.case_id, "checks": mechanical_checks(row)} for row in records]
    # The lesson's self-checks validate fixture wiring, not semantic model quality.
    assert mechanical_checks(wrong_claim)["citation_integrity"] is True
    assert mechanical_checks(bad_quote)["citation_integrity"] is False
    assert mechanical_checks(missing_circular)["child_reference_coverage"] == 0
    assert mechanical_checks(abstention)["status_matches"] is True
    return {
        "mode": "controlled_offline_demo",
        "live_calls": False,
        "semantic_scores": "not_measured",
        "gate": "not_evaluated",
        "fixture_note": "Constructed text from synthetic policy facts; not literal PDF quotations.",
        "cases": rows,
    }
