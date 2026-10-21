from __future__ import annotations

import asyncio
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.evaluation import run as evaluation
from app.evaluation.run import JudgeScore, load_cases, quality_gate


def test_phase1_cases_include_supported_and_abstention_questions() -> None:
    cases = load_cases(Path("evaluation/datasets/answer.jsonl"))
    assert len(cases) == 10
    assert sum(case.expected_status == "insufficient_evidence" for case in cases) == 2
    assert all(case.context for case in cases if case.expected_status == "answered")


def test_quality_gate_rejects_low_quality_and_wrong_abstention() -> None:
    report: dict[str, Any] = {
        "ragas": {"means": {"faithfulness": 0.9}},
        "records": [{"judge": {"correctness": 0.9, "groundedness": 0.9, "status_matches": True}}],
    }
    assert quality_gate(report, 0.8)
    report["records"][0]["judge"]["status_matches"] = False
    assert not quality_gate(report, 0.8)
    with pytest.raises(ValidationError):
        JudgeScore(correctness=float("nan"), groundedness=1, rationale="invalid")


def test_ragas_scores_actual_text_and_penalizes_missing_evidence(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    monkeypatch.setenv("RAGAS_DO_NOT_TRACK", "true")
    settings = settings.model_copy(update={"eval_judge_model": "separate-test-judge"})
    model_factory = Mock(wraps=evaluation.get_chat_model)
    embeddings_factory = Mock(wraps=evaluation.get_embeddings)
    monkeypatch.setattr(evaluation, "get_chat_model", model_factory)
    monkeypatch.setattr(evaluation, "get_embeddings", embeddings_factory)
    pytest.importorskip("ragas")
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    scorers = []
    for metric in (Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall):
        score = AsyncMock(return_value=SimpleNamespace(value=0.9))
        monkeypatch.setattr(metric, "ascore", score)
        scorers.append(score)
    record = {
        "expected_status": "answered",
        "user_input": "limit?",
        "response": "7.5 crore",
        "reference": "7.5 crore",
        "retrieved_contexts": ["Actual supplied policy text"],
    }
    result = asyncio.run(
        evaluation.evaluate_ragas([record, {**record, "retrieved_contexts": []}], settings)
    )
    assert result["case_count"] == 2
    assert result["means"]["context_recall"] == 0.45
    assert scorers[0].await_args is not None
    assert scorers[0].await_args.kwargs["retrieved_contexts"] == ["Actual supplied policy text"]
    assert all(score.await_count == 1 for score in scorers)
    assert model_factory.call_args.args[0].chat_model == "separate-test-judge"
    assert (
        embeddings_factory.call_args.args[0].embedding_dimensions == settings.embedding_dimensions
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 1.01, -0.01, 1.0000000000000002])
def test_batch_metrics_validate_scores_like_live_metrics(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, value: float
) -> None:
    pytest.importorskip("ragas")
    from app.evaluation import ragas_metrics
    from app.models.evaluation import METRIC_NAMES

    scorer = SimpleNamespace(
        metrics={
            name: SimpleNamespace(ascore=AsyncMock(return_value=SimpleNamespace(value=value)))
            for name in METRIC_NAMES
        }
    )
    monkeypatch.setattr(ragas_metrics, "RagasScorer", lambda *_: scorer)
    monkeypatch.setattr(evaluation, "get_chat_model", lambda _: object())
    monkeypatch.setattr(evaluation, "get_embeddings", lambda _: object())
    record = {
        "expected_status": "answered",
        "user_input": "limit?",
        "response": "7.5 crore",
        "reference": "7.5 crore",
        "retrieved_contexts": ["Maximum is 7.5 crore."],
    }
    if value == 1.0000000000000002:
        result = asyncio.run(evaluation.evaluate_ragas([record], settings))
        assert result["scores"] == [dict.fromkeys(METRIC_NAMES, 1.0)]
    else:
        with pytest.raises(ValidationError):
            asyncio.run(evaluation.evaluate_ragas([record], settings))


@pytest.mark.parametrize("datadog_enabled", [False, True])
def test_evaluation_reuses_generation_evidence_and_collects_trace(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, datadog_enabled: bool
) -> None:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.runnables import RunnableLambda

    from app.models.answer import AnswerDraft
    from app.models.retrieval import RetrieveResponse

    span = object()
    datadog = SimpleNamespace(
        enabled=datadog_enabled,
        workflow=Mock(return_value=nullcontext(span)),
        annotate=Mock(),
        export_span=Mock(return_value={"trace_id": "1", "span_id": "2"}),
    )
    monkeypatch.setattr(evaluation, "LLMObs", datadog)
    response = RetrieveResponse.model_validate(
        {
            "as_of": "2026-10-01",
            "results": [
                {
                    "rank": 1,
                    "score": 0.9,
                    "text": "Maximum is 7.5 crore.",
                    "parent_text": "Maximum is 7.5 crore.",
                    "citation": {
                        "doc_id": "POL-HL-V3",
                        "title": "Home Loan",
                        "policy_version": "3",
                        "clause": "4.1",
                        "effective_date": "2025-10-01",
                    },
                }
            ],
            "timings": {"search_ms": 1, "parent_ms": 1, "total_ms": 2},
        }
    )
    retrieval = AsyncMock(return_value=response)
    monkeypatch.setattr(evaluation, "retrieve_policy", retrieval)
    monkeypatch.setattr(
        evaluation, "resolve_reference_contexts", lambda *_: ["Reference source text"]
    )
    model = Mock(spec=BaseChatModel)

    def structured(schema: Any, **_: Any) -> Any:
        if schema is AnswerDraft:
            return RunnableLambda(
                lambda _: {
                    "status": "answered",
                    "answer": "7.5 crore [1]",
                    "evidence": [{"evidence_id": 1, "quote": "7.5 crore"}],
                }
            )
        return RunnableLambda(
            lambda _: {
                "correctness": 0.9,
                "groundedness": 1,
                "rationale": "controlled fixture",
            }
        )

    model.with_structured_output.side_effect = structured
    settings = settings.model_copy(update={"eval_judge_model": "separate-test-judge"})
    configured_models: list[str] = []

    def get_model(config: Settings) -> Any:
        configured_models.append(config.chat_model)
        return model

    monkeypatch.setattr(evaluation, "get_chat_model", get_model)
    records = asyncio.run(
        evaluation.collect_records(
            load_cases(Path("evaluation/datasets/answer.jsonl"))[:1], settings
        )
    )
    assert retrieval.await_count == 1
    assert configured_models == [settings.chat_model, "separate-test-judge"]
    assert records[0]["retrieved_contexts"] == ["Maximum is 7.5 crore."]
    assert records[0]["judge"]["status_matches"] is True
    assert {span["name"] for span in records[0]["trace"]} >= {
        "evaluation_retrieval",
        "answer_policy",
    }
    if datadog_enabled:
        assert records[0]["datadog_span"] == {"trace_id": "1", "span_id": "2"}
        assert datadog.annotate.call_args.kwargs["input_data"] == records[0]["request"]
        assert datadog.annotate.call_args.kwargs["output_data"]["answer"] == "7.5 crore [1]"
        datadog.export_span.assert_called_once_with(span)
    else:
        assert "datadog_span" not in records[0]
        datadog.workflow.assert_not_called()
        datadog.annotate.assert_not_called()


def test_datadog_scores_join_the_correct_case_and_skip_ragas_for_abstentions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    submit = Mock()
    monkeypatch.setattr(evaluation.LLMObs, "submit_evaluation", submit)
    records = [
        {
            "expected_status": expected,
            "datadog_span": {"trace_id": str(i), "span_id": str(i)},
            "judge": {
                "correctness": 0.7,
                "groundedness": 0.8,
                "status_matches": i != 1,
                "rationale": "controlled fixture",
            },
        }
        for i, expected in enumerate(("insufficient_evidence", "answered", "answered"))
    ]
    scores = [
        dict.fromkeys(
            ("faithfulness", "answer_relevancy", "context_precision", "context_recall"), value
        )
        for value in (0.2, 0.9)
    ]
    assert evaluation.publish_datadog_evaluations(records, {"scores": scores}) == 17
    sent = {
        (call.kwargs["span"]["span_id"], call.kwargs["label"]): call.kwargs
        for call in submit.call_args_list
    }
    assert all(span_id != "0" for span_id, label in sent if label.startswith("ragas_"))
    assert sent["1", "ragas_faithfulness"]["value"] == 0.2
    assert sent["2", "ragas_faithfulness"]["value"] == 0.9
    assert sent["0", "judge_groundedness"]["reasoning"] == "controlled fixture"
    assert sent["1", "status_matches"]["assessment"] == "fail"
    assert all(call.kwargs["eval_scope"] == "span" for call in submit.call_args_list)


@pytest.mark.parametrize("enabled", [False, True])
def test_datadog_export_is_optional_and_flushes_when_enabled(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, enabled: bool
) -> None:
    datadog = SimpleNamespace(enabled=enabled, flush=Mock())
    monkeypatch.setattr(evaluation, "LLMObs", datadog)
    monkeypatch.setattr(evaluation, "collect_records", AsyncMock(return_value=[]))
    monkeypatch.setattr(evaluation, "evaluate_ragas", AsyncMock(return_value={"scores": []}))
    publish = Mock(return_value=0)
    monkeypatch.setattr(evaluation, "publish_datadog_evaluations", publish)
    settings = settings.model_copy(update={"eval_judge_model": "separate-test-judge"})
    result = asyncio.run(evaluation.run([], settings))
    assert result["judge_model"] == "separate-test-judge"
    assert result["datadog"]["status"] == ("queued" if enabled else "disabled")
    assert publish.call_count == int(enabled)
    assert datadog.flush.call_count == int(enabled)
