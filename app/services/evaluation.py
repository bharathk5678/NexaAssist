from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

import structlog
from ddtrace.llmobs import LLMObs
from langchain_core.runnables import RunnableLambda

from app.chains.answer import build_answer_chain
from app.chains.context import assemble_context
from app.chains.llm import get_chat_model
from app.core.config import Settings
from app.evaluation.live import score_answer
from app.evaluation.run import load_cases
from app.models.evaluation import AnswerQuality, EvaluatedAnswerRequest, EvaluatedAnswerResponse
from app.models.retrieval import RetrieveRequest
from app.services.retrieval import retrieve_policy

logger = structlog.get_logger()
GOLDEN_DATASET = Path(__file__).resolve().parents[2] / "evaluation/datasets/answer.jsonl"


async def answer_with_quality(
    request: EvaluatedAnswerRequest, settings: Settings
) -> EvaluatedAnswerResponse:
    policy_request = RetrieveRequest.model_validate(
        request.model_dump(exclude={"reference_answer"})
    )
    reference = request.reference_answer
    source: Literal["provided", "golden_dataset", "none"] = "provided" if reference else "none"
    if reference is None and GOLDEN_DATASET.is_file():
        try:
            cases = load_cases(GOLDEN_DATASET)
        except (OSError, ValueError) as exc:
            logger.warning("golden_reference_unavailable", error_type=type(exc).__name__)
            cases = []
        for case in cases:
            if (
                case.expected_status == "answered"
                and case.input.query.casefold().rstrip("?") == request.query.casefold().rstrip("?")
                and case.input.as_of == request.as_of
                and case.input.product_id == request.product_id
                and case.input.jurisdiction == request.jurisdiction
            ):
                reference, source = case.expected_output, "golden_dataset"
                break

    started = datetime.now(UTC)
    with (
        LLMObs.workflow(name="policy_answer_live_evaluation", agent_service=settings.dd_service)
        if LLMObs.enabled
        else nullcontext()
    ) as span:
        retrieved = await retrieve_policy(policy_request, settings)
        chain = build_answer_chain(
            RunnableLambda(lambda _: retrieved), get_chat_model(settings), settings
        )
        answer = await chain.ainvoke(policy_request)
        contexts = [
            hit.parent_text
            for hit in assemble_context(
                retrieved.evidence, settings.context_max_tokens, settings.token_encoding
            ).values()
        ]
        metrics = await score_answer(request.query, answer, contexts, reference, settings)
        quality = AnswerQuality(
            metrics=metrics,
            reference_source=source,
            reference_answer=reference,
            evaluated_at=datetime.now(UTC),
        )
        if span is not None:
            try:
                LLMObs.annotate(
                    span=span,
                    input_data=policy_request.model_dump(mode="json"),
                    output_data=answer.model_dump(mode="json"),
                    metadata={
                        "reference_source": source,
                        "reference": reference,
                        "judge_model": settings.eval_judge_model or settings.chat_model,
                        "ragas": {name: metric.model_dump() for name, metric in metrics.items()},
                    },
                    tags={"operation": "live_evaluation"},
                )
                exported = LLMObs.export_span(span)
                if exported is None:
                    raise ValueError("Datadog did not export a workflow span reference")
                reference_span = {"trace_id": exported["trace_id"], "span_id": exported["span_id"]}
                answer.datadog_span_id = exported["span_id"]
                for name, metric in metrics.items():
                    if metric.status == "scored" and metric.value is not None:
                        LLMObs.submit_evaluation(
                            span=reference_span,
                            label=f"ragas_{name}",
                            metric_type="score",
                            value=metric.value,
                            tags={"evaluation_provider": "ragas"},
                            eval_scope="span",
                        )
                quality.datadog_status = (
                    "queued"
                    if any(m.status == "scored" for m in metrics.values())
                    else "not_scored"
                )
                query = urlencode(
                    {
                        "query": f"service:{settings.dd_service} @name:policy_answer_live_evaluation",
                        "start": int(started.timestamp() * 1000) - 60000,
                        "end": int(quality.evaluated_at.timestamp() * 1000) + 60000,
                        "paused": "true",
                    }
                )
                quality.datadog_url = f"https://app.{settings.dd_site}/llm/traces?{query}"
            except Exception as exc:  # noqa: BLE001 - preserve scores when optional telemetry fails
                quality.datadog_status = "error"
                logger.warning("ragas_datadog_publish_failed", error_type=type(exc).__name__)
        logger.info(
            "answer_quality_completed",
            reference_source=source,
            metric_statuses={name: metric.status for name, metric in metrics.items()},
            datadog_status=quality.datadog_status,
        )
        return EvaluatedAnswerResponse(answer=answer, quality=quality)
