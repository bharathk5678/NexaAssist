from __future__ import annotations

import argparse
import asyncio
import json
from contextlib import nullcontext
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any, Literal

import structlog
from ddtrace.llmobs import LLMObs
from langchain_core.runnables import RunnableLambda
from langchain_core.tracers.run_collector import RunCollectorCallbackHandler
from langsmith import traceable
from pydantic import BaseModel, ConfigDict, Field

from app.chains.answer import build_answer_chain
from app.chains.context import assemble_context
from app.chains.embeddings import get_embeddings
from app.chains.llm import get_chat_model
from app.chains.prompts.judge import JUDGE_PROMPT, JUDGE_VERSION
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.database.retrieval import resolve_reference_contexts
from app.models.evaluation import METRIC_NAMES, QualityScore
from app.models.retrieval import RetrieveRequest, RetrieveResponse
from app.services.retrieval import retrieve_policy

ROOT = Path(__file__).resolve().parents[2]
logger = structlog.get_logger()


class GoldenCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: RetrieveRequest
    expected_output: str
    context: list[dict[str, Any]]
    expected_status: Literal["answered", "insufficient_evidence"] = "answered"


class JudgeScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correctness: float = Field(ge=0, le=1, allow_inf_nan=False)
    groundedness: float = Field(ge=0, le=1, allow_inf_nan=False)
    rationale: str


def load_cases(path: Path) -> list[GoldenCase]:
    cases = [
        GoldenCase.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    if not cases:
        raise ValueError("Evaluation dataset is empty")
    return cases


def trace_summary(runs: list[Any]) -> list[dict[str, Any]]:
    spans = []
    for run in runs:
        spans.append(
            {
                "name": run.name,
                "run_type": run.run_type,
                "duration_ms": round((run.end_time - run.start_time).total_seconds() * 1000, 2)
                if run.end_time
                else None,
                "failed": bool(run.error),
            }
        )
        spans.extend(trace_summary(run.child_runs))
    return spans


@traceable
async def collect_records(cases: list[GoldenCase], settings: Settings) -> list[dict[str, Any]]:
    """Generate once per case; evaluate the exact evidence passed to that generation."""
    model = get_chat_model(settings)
    judge_settings = settings.model_copy(
        update={"chat_model": settings.eval_judge_model or settings.chat_model}
    )
    judge = JUDGE_PROMPT | get_chat_model(judge_settings).with_structured_output(
        JudgeScore, method="json_schema", strict=True
    )
    records = []
    for case in cases:
        with (
            LLMObs.workflow(name="policy_answer_evaluation") if LLMObs.enabled else nullcontext()
        ) as span:
            reference_contexts = await asyncio.to_thread(
                resolve_reference_contexts, settings, case.context
            )
            collector = RunCollectorCallbackHandler()

            async def retrieve(request: RetrieveRequest) -> RetrieveResponse:
                return await retrieve_policy(request, settings)

            retrieved = (
                await RunnableLambda(retrieve)
                .with_config(run_name="evaluation_retrieval")
                .ainvoke(case.input, config={"callbacks": [collector]})
            )
            sources = assemble_context(
                retrieved.results, settings.context_max_tokens, settings.token_encoding
            )

            def replay(
                _request: RetrieveRequest, evidence: RetrieveResponse = retrieved
            ) -> RetrieveResponse:
                return evidence

            chain = build_answer_chain(RunnableLambda(replay), model, settings)
            answer = await chain.ainvoke(case.input, config={"callbacks": [collector]})
            record: dict[str, Any] = {
                "user_input": case.input.query,
                "response": answer.answer,
                "reference": case.expected_output,
                "reference_contexts": reference_contexts,
                "retrieved_contexts": [hit.parent_text for hit in sources.values()],
                "expected_status": case.expected_status,
                "actual_status": answer.status,
            }
            score = JudgeScore.model_validate(
                await judge.ainvoke({"record": json.dumps(record, ensure_ascii=False)})
            )
            record.update(
                request=case.input.model_dump(mode="json"),
                retrieval_timings=retrieved.timings.model_dump(),
                generation_ms=answer.generation_ms,
                trace=trace_summary(collector.traced_runs),
                judge={
                    **score.model_dump(),
                    "status_matches": answer.status == case.expected_status,
                },
            )
            if span is not None:
                LLMObs.annotate(
                    span=span,
                    input_data=record["request"],
                    output_data=answer.model_dump(mode="json"),
                    metadata={
                        "reference": case.expected_output,
                        "judge_prompt_version": JUDGE_VERSION,
                        "judge_model": judge_settings.chat_model,
                        "retrieval_mode": settings.retrieval_mode,
                        "rerank_enabled": settings.rerank_enabled,
                    },
                    tags={"operation": "offline_evaluation"},
                )
                record["datadog_span"] = LLMObs.export_span(span)
            records.append(record)
    return records


@traceable
async def evaluate_ragas(records: list[dict[str, Any]], settings: Settings) -> dict[str, Any]:
    from app.evaluation.ragas_metrics import RagasScorer

    eligible = [record for record in records if record["expected_status"] == "answered"]
    if not eligible:
        return {"status": "not_applicable", "case_count": 0, "scores": [], "means": {}}
    scores = []
    judge_settings = settings.model_copy(
        update={"chat_model": settings.eval_judge_model or settings.chat_model}
    )
    scorer = RagasScorer(get_chat_model(judge_settings), get_embeddings(settings))
    for record in eligible:
        question, response = record["user_input"], record["response"]
        contexts, reference = record["retrieved_contexts"], record["reference"]
        if not contexts:
            # Retrieval failed for an answerable case. Do not give abstention a free pass.
            scores.append(dict.fromkeys(METRIC_NAMES, 0.0))
            continue
        results = await asyncio.gather(
            *(
                asyncio.wait_for(
                    scorer.metrics[name].ascore(
                        user_input=question,
                        **({"retrieved_contexts": contexts} if name != "answer_relevancy" else {}),
                        **(
                            {"response": response}
                            if name in ("faithfulness", "answer_relevancy")
                            else {"reference": reference}
                        ),
                    ),
                    timeout=120,
                )
                for name in METRIC_NAMES
            )
        )
        row = {}
        for name, result in zip(METRIC_NAMES, results, strict=True):
            metric = QualityScore(status="scored", value=float(result.value))
            assert metric.value is not None  # A scored QualityScore always has a value.
            row[name] = metric.value
        scores.append(row)
    means = {key: sum(row[key] for row in scores) / len(scores) for key in scores[0]}
    return {"status": "completed", "case_count": len(scores), "scores": scores, "means": means}


def quality_gate(report: dict[str, Any], minimum: float | None) -> bool:
    if minimum is None:
        return True
    values = list(report["ragas"]["means"].values())
    values.extend(
        record["judge"][key]
        for record in report["records"]
        for key in ("correctness", "groundedness")
    )
    return (
        bool(values)
        and all(value >= minimum for value in values)
        and all(record["judge"]["status_matches"] for record in report["records"])
    )


def publish_datadog_evaluations(records: list[dict[str, Any]], ragas: dict[str, Any]) -> int:
    """Join existing scores to the generation's workflow, including abstention cases."""
    scores = iter(ragas["scores"])
    count = 0
    for record in records:
        metrics = {f"judge_{key}": record["judge"][key] for key in ("correctness", "groundedness")}
        if record["expected_status"] == "answered":
            metrics.update({f"ragas_{key}": value for key, value in next(scores).items()})
        for label, value in metrics.items():
            LLMObs.submit_evaluation(
                span=record["datadog_span"],
                label=label,
                metric_type="score",
                value=value,
                reasoning=record["judge"]["rationale"] if label.startswith("judge_") else None,
                tags={
                    "evaluation_provider": "llm_judge" if label.startswith("judge_") else "ragas"
                },
                eval_scope="span",
            )
            count += 1
        matches = record["judge"]["status_matches"]
        LLMObs.submit_evaluation(
            span=record["datadog_span"],
            label="status_matches",
            metric_type="boolean",
            value=matches,
            assessment="pass" if matches else "fail",
            eval_scope="span",
        )
        count += 1
    return count


async def run(cases: list[GoldenCase], settings: Settings) -> dict[str, Any]:
    records = await collect_records(cases, settings)
    ragas = await evaluate_ragas(records, settings)
    datadog: dict[str, Any] = {"status": "disabled"}
    if LLMObs.enabled:
        datadog = {
            "status": "queued",
            "evaluation_count": publish_datadog_evaluations(records, ragas),
        }
        await asyncio.to_thread(LLMObs.flush)
    return {
        "status": "completed",
        "captured_at": datetime.now(UTC).isoformat(),
        "model": settings.chat_model,
        "judge_model": settings.eval_judge_model or settings.chat_model,
        "judge_prompt_version": JUDGE_VERSION,
        "judge_limitation": "Stochastic scoring; review with humans."
        + (
            " Same-model self-preference is possible."
            if (settings.eval_judge_model or settings.chat_model) == settings.chat_model
            else " A separate judge model does not guarantee independent errors."
        ),
        "retrieval_mode": settings.retrieval_mode,
        "rerank_enabled": settings.rerank_enabled,
        "rerank_model": settings.rerank_model if settings.rerank_enabled else None,
        "ragas_version": version("ragas"),
        "empty_context_policy": "Answerable cases with no evidence receive zero metrics.",
        "records": records,
        "ragas": ragas,
        "datadog": datadog,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 1 RAGAS and LLM-as-Judge evaluation")
    parser.add_argument("--dataset", type=Path, default=ROOT / "evaluation/datasets/answer.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "app/evaluation/results/latest.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--min-score", type=float, help="Explicit 0–1 quality gate; no assumed target"
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.min_score is not None and not 0 <= args.min_score <= 1:
        parser.error("--min-score must be between 0 and 1")
    configure_logging("INFO")
    try:
        cases = load_cases(args.dataset)
        report = asyncio.run(run(cases[: args.limit], get_settings()))
        report["dataset"] = str(args.dataset)
        report["gate"] = {
            "minimum": args.min_score,
            "status": "not_configured"
            if args.min_score is None
            else "passed"
            if quality_gate(report, args.min_score)
            else "failed",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
        structlog.get_logger().info(
            "evaluation_completed",
            output=str(args.output),
            cases=len(report["records"]),
            gate=report["gate"],
        )
    except Exception as exc:
        logger.exception("evaluation_failed", error_type=type(exc).__name__)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "captured_at": datetime.now(UTC).isoformat(),
                    "error_type": type(exc).__name__,
                    "gate": {"status": "failed"},
                },
                indent=2,
            )
        )
        raise SystemExit(1) from None
    if report["gate"]["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
