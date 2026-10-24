from __future__ import annotations

import asyncio

import structlog
from pydantic import ValidationError

from app.chains.embeddings import get_embeddings
from app.chains.llm import get_chat_model
from app.core.config import Settings
from app.models.answer import AnswerResponse
from app.models.evaluation import METRIC_NAMES, MetricName, QualityScore

logger = structlog.get_logger()


async def score_answer(
    query: str,
    answer: AnswerResponse,
    contexts: list[str],
    reference: str | None,
    settings: Settings,
) -> dict[MetricName, QualityScore]:
    """Score the generated answer and its exact evidence; never retrieve or regenerate."""
    scores: dict[MetricName, QualityScore] = {}
    for name in METRIC_NAMES:
        reason = None
        if not contexts:
            reason = "No retrieved evidence was available."
        elif name in ("context_precision", "context_recall") and reference is None:
            reason = "Provide a reference answer, or use an exactly matching golden case."
        elif name in ("faithfulness", "answer_relevancy") and answer.status != "answered":
            reason = "The answer abstained; this metric is not applicable."
        if reason:
            scores[name] = QualityScore(status="unavailable", reason=reason)
    if len(scores) == len(METRIC_NAMES):
        return scores

    try:
        from app.evaluation.ragas_metrics import RagasScorer

        judge_settings = settings.model_copy(
            update={"chat_model": settings.eval_judge_model or settings.chat_model}
        )
        scorer = RagasScorer(get_chat_model(judge_settings), get_embeddings(settings))
    except Exception as exc:  # noqa: BLE001 - optional evaluator failure must preserve the answer
        logger.warning("ragas_initialization_failed", error_type=type(exc).__name__)
        for name in METRIC_NAMES:
            scores.setdefault(
                name,
                QualityScore(
                    status="error", reason=f"RAGAS initialization failed ({type(exc).__name__})."
                ),
            )
        return scores

    async def measure(name: MetricName) -> None:
        inputs: dict[str, object] = {"user_input": query}
        if name != "answer_relevancy":
            inputs["retrieved_contexts"] = contexts
        if name in ("faithfulness", "answer_relevancy"):
            inputs["response"] = answer.answer
        else:
            inputs["reference"] = reference
        try:
            result = await asyncio.wait_for(scorer.metrics[name].ascore(**inputs), timeout=120)
            scores[name] = QualityScore(status="scored", value=float(result.value))
        except Exception as exc:  # noqa: BLE001 - isolate each external scoring boundary
            logger.warning(
                "ragas_metric_failed",
                metric=name,
                error_type=type(exc).__name__,
                validation_errors=exc.errors(
                    include_input=False, include_context=False, include_url=False
                )
                if isinstance(exc, ValidationError)
                else None,
            )
            scores[name] = QualityScore(
                status="error", reason=f"Scoring failed ({type(exc).__name__})."
            )

    await asyncio.gather(*(measure(name) for name in METRIC_NAMES if name not in scores))
    return {name: scores[name] for name in METRIC_NAMES}
