"""Regression tests for phase gate."""

from __future__ import annotations

import copy
import json
import runpy
import sys
from pathlib import Path

import pytest

from app.evaluation import phase_gate
from app.evaluation.run import load_cases
from app.models.evaluation import METRIC_NAMES

DATASET = Path("evaluation/datasets/answer.jsonl")


@pytest.fixture
def report() -> dict:
    """Provide report for the phase gate scenario.

    Returns:
        Named values describing the documented operation or diagnostic outcome.
    """
    cases = load_cases(DATASET)
    answered = sum(case.expected_status == "answered" for case in cases)
    return {
        "status": "completed",
        "model": "fake-answer",
        "judge_model": "fake-judge",
        "judge_prompt_version": "policy-judge-v2",
        "ragas_version": "0.4.3",
        "retrieval_mode": "dense",
        "rerank_enabled": False,
        "rerank_model": None,
        "records": [
            {
                "request": c.input.model_dump(mode="json"),
                "reference": c.expected_output,
                "expected_status": c.expected_status,
                "actual_status": c.expected_status,
                "retrieved_contexts": ["Fake evidence for gate mechanics"],
                "judge": {
                    "correctness": 0.9,
                    "groundedness": 0.9,
                    "rationale": "Mocked gate test",
                    "status_matches": True,
                },
            }
            for c in cases
        ],
        "ragas": {
            "status": "completed",
            "case_count": answered,
            "scores": [dict.fromkeys(METRIC_NAMES, 0.9) for _ in range(answered)],
            "means": dict.fromkeys(METRIC_NAMES, 0.9),
        },
    }


def test_each_metric_and_judge_mean_cannot_regress(report: dict) -> None:
    """Verify each metric and judge mean cannot regress.

    Args:
        report: Measured quality or security report to validate.
    """
    baseline = phase_gate.measured_baseline(report, DATASET)
    assert phase_gate.compare(report, baseline, DATASET)["status"] == "passed"
    assert baseline["case_count"] == 10
    assert len(baseline["minimum_means"]) == 6
    for name in METRIC_NAMES:
        candidate = copy.deepcopy(report)
        candidate["ragas"]["scores"][0][name] = 0.1
        candidate["ragas"]["means"][name] = (
            sum(row[name] for row in candidate["ragas"]["scores"])
            / candidate["ragas"]["case_count"]
        )
        assert phase_gate.compare(candidate, baseline, DATASET)["regressions"] == [name]
    report["records"][0]["judge"]["correctness"] = 0.1
    assert phase_gate.compare(report, baseline, DATASET)["regressions"] == ["judge_correctness"]


@pytest.mark.parametrize(
    "invalid",
    [
        "partial",
        "status",
        "wrong_scope",
        "wrong_reference",
        "expected_status",
        "empty_evidence",
        "missing_metric",
        "nan",
        "bool",
        "mean",
        "case_count",
        "missing_scores",
        "failed_ragas",
        "failed_run",
        "judge",
    ],
)
def test_incomplete_or_invalid_evidence_cannot_become_baseline(report: dict, invalid: str) -> None:
    """Verify incomplete or invalid evidence cannot become baseline.

    Args:
        report: Measured quality or security report to validate.
        invalid: Invalid fixture or parametrized input for this scenario.
    """
    if invalid == "partial":
        report["records"].pop()
    elif invalid == "status":
        report["records"][0]["actual_status"] = "insufficient_evidence"
    elif invalid == "wrong_scope":
        report["records"][0]["request"]["as_of"] = "2020-01-01"
    elif invalid == "wrong_reference":
        report["records"][0]["reference"] = "Different golden answer"
    elif invalid == "expected_status":
        report["records"][0]["expected_status"] = "needs_clarification"
    elif invalid == "empty_evidence":
        report["records"][0]["retrieved_contexts"] = []
    elif invalid == "missing_metric":
        report["ragas"]["means"].pop("faithfulness")
    elif invalid in ("nan", "bool"):
        report["ragas"]["scores"][0]["faithfulness"] = float("nan") if invalid == "nan" else True
    elif invalid == "mean":
        report["ragas"]["means"]["faithfulness"] = 1
    elif invalid == "case_count":
        report["ragas"]["case_count"] -= 1
    elif invalid == "missing_scores":
        report["ragas"]["scores"].pop()
    elif invalid == "failed_ragas":
        report["ragas"]["status"] = "error"
    elif invalid == "failed_run":
        report["status"] = "failed"
    else:
        report["records"][0]["judge"]["groundedness"] = float("inf")
    with pytest.raises(ValueError):
        phase_gate.measured_baseline(report, DATASET)


@pytest.mark.parametrize("invalid", ["protocol", "dataset", "floors", "nonfinite"])
def test_baseline_changes_are_explicit(report: dict, invalid: str) -> None:
    """Verify baseline changes are explicit.

    Args:
        report: Measured quality or security report to validate.
        invalid: Invalid fixture or parametrized input for this scenario.
    """
    baseline = phase_gate.measured_baseline(report, DATASET)
    if invalid == "protocol":
        baseline["protocol"]["model"] = "different-model"
    elif invalid == "dataset":
        baseline["dataset_sha256"] = "changed"
    elif invalid == "floors":
        baseline["minimum_means"].pop("judge_groundedness")
    else:
        baseline["minimum_means"]["judge_groundedness"] = float("nan")
    with pytest.raises(ValueError):
        phase_gate.compare(report, baseline, DATASET)


def test_cli_captures_checks_blocks_regression_and_refuses_overwrite(
    report: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify cli captures checks blocks regression and refuses overwrite.

    Args:
        report: Measured quality or security report to validate.
        tmp_path: Isolated temporary directory for this test's files.
        monkeypatch: Pytest fixture used to isolate dependencies for this scenario.
    """
    path, baseline = tmp_path / "report.json", tmp_path / "baseline.json"
    path.write_text(json.dumps(report))

    def run(operation: str) -> None:
        monkeypatch.setattr(
            sys,
            "argv",
            ["phase_gate", operation, "--report", str(path), "--baseline", str(baseline)],
        )
        runpy.run_path(str(Path(phase_gate.__file__)), run_name="__main__")

    run("capture")
    captured = baseline.read_bytes()
    run("check")
    with pytest.raises(SystemExit, match="1"):
        run("capture")
    assert baseline.read_bytes() == captured
    report["records"][0]["judge"]["correctness"] = 0
    path.write_text(json.dumps(report))
    with pytest.raises(SystemExit, match="1"):
        run("check")
    path.write_text("not json")
    with pytest.raises(SystemExit, match="1"):
        run("check")
