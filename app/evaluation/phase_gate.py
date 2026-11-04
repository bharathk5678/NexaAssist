"""Fail-closed release comparison against an explicitly captured full-dataset baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from math import isfinite
from pathlib import Path
from typing import Any

import structlog

from app.core.logging import configure_logging
from app.evaluation.run import JudgeScore, load_cases
from app.models.evaluation import METRIC_NAMES

PROTOCOL_FIELDS = (
    "model",
    "judge_model",
    "judge_prompt_version",
    "ragas_version",
    "retrieval_mode",
    "rerank_enabled",
    "rerank_model",
)


def measured_baseline(report: dict[str, Any], dataset: Path) -> dict[str, Any]:
    """Validate a complete scored report and capture its dataset/model protocol identity.

    Args:
        report: Measured quality or security report to validate.
        dataset: Golden dataset file used by this evaluation.

    Raises:
        ValueError: RAGAS means do not match the measured case scores.
    """
    cases = load_cases(dataset)
    records, ragas = report["records"], report["ragas"]
    if report["status"] != "completed" or len(records) != len(cases):
        raise ValueError("A completed full-dataset evaluation is required")
    judge_scores = []
    for record, case in zip(records, cases, strict=True):
        if (
            record["request"] != case.input.model_dump(mode="json")
            or record["reference"] != case.expected_output
            or record["expected_status"] != case.expected_status
        ):
            raise ValueError("Evaluation cases do not match the versioned golden dataset")
        if (
            record["actual_status"] != case.expected_status
            or record["judge"]["status_matches"] is not True
        ):
            raise ValueError("Golden answer statuses failed")
        if case.expected_status == "answered" and not record["retrieved_contexts"]:
            raise ValueError("An answerable case has no retrieved evidence")
        judge_scores.append(
            JudgeScore.model_validate(
                {k: record["judge"][k] for k in ("correctness", "groundedness", "rationale")}
            )
        )
    eligible = sum(case.expected_status == "answered" for case in cases)
    if (
        ragas["status"] != "completed"
        or ragas["case_count"] != eligible
        or len(ragas["scores"]) != eligible
    ):
        raise ValueError("All answerable cases require all four RAGAS metrics")
    means: dict[str, float] = {}
    for row in [*ragas["scores"], ragas["means"]]:
        if set(row) != set(METRIC_NAMES) or any(
            type(v) not in (int, float) or not isfinite(v) or not 0 <= v <= 1 for v in row.values()
        ):
            raise ValueError("RAGAS scores must be complete finite probabilities")
    for name in METRIC_NAMES:
        value = sum(row[name] for row in ragas["scores"]) / eligible
        if abs(value - ragas["means"][name]) > 1e-9:
            raise ValueError("RAGAS means do not match the measured case scores")
        means[name] = value
    for judge_name in ("correctness", "groundedness"):
        means["judge_" + judge_name] = sum(getattr(s, judge_name) for s in judge_scores) / len(
            cases
        )
    return {
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "case_count": len(cases),
        "protocol": {name: report[name] for name in PROTOCOL_FIELDS},
        "minimum_means": means,
    }


def compare(report: dict[str, Any], baseline: dict[str, Any], dataset: Path) -> dict[str, Any]:
    """Reject missing, incompatible or regressed release-quality measurements.

    Args:
        report: Measured quality or security report to validate.
        baseline: Previously reviewed measured values or finding fingerprints.
        dataset: Golden dataset file used by this evaluation.

    Raises:
        ValueError: The evaluation baseline is invalid.
    """
    candidate = measured_baseline(report, dataset)
    if any(candidate[key] != baseline[key] for key in ("dataset_sha256", "case_count", "protocol")):
        raise ValueError("Dataset or scoring protocol changed; capture and review a new baseline")
    floors = baseline["minimum_means"]
    if set(floors) != set(candidate["minimum_means"]) or any(
        type(v) not in (int, float) or not isfinite(v) or not 0 <= v <= 1 for v in floors.values()
    ):
        raise ValueError("The evaluation baseline is invalid")
    regressions = [
        name for name, value in candidate["minimum_means"].items() if value + 1e-9 < floors[name]
    ]
    return {
        "status": "failed" if regressions else "passed",
        "regressions": regressions,
        "means": candidate["minimum_means"],
    }


def main() -> None:
    """Run the phase gate command with validated arguments and explicit outcomes.

    Raises:
        SystemExit: The operation cannot satisfy its documented validation or execution contract.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("capture", "check"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=Path("evaluation/datasets/answer.jsonl"))
    parser.add_argument("--baseline", type=Path, required=True)
    args = parser.parse_args()
    configure_logging("INFO")
    try:
        report = json.loads(args.report.read_text())
        if args.operation == "capture":
            baseline = measured_baseline(report, args.dataset)
            args.baseline.parent.mkdir(parents=True, exist_ok=True)
            with args.baseline.open("x") as output:
                json.dump(baseline, output, indent=2, allow_nan=False)
                output.write("\n")
            result = {"status": "captured", "means": baseline["minimum_means"]}
        else:
            result = compare(report, json.loads(args.baseline.read_text()), args.dataset)
    except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        structlog.get_logger().error("phase1_gate_invalid", error_type=type(exc).__name__)
        raise SystemExit(1) from None
    structlog.get_logger().info("phase1_gate", **result)
    if result["status"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
