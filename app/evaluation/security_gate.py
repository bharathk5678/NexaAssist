"""Compare redacted security fingerprints against the reviewed source baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import structlog

from app.core.logging import configure_logging


def finding_fingerprint(result: dict[str, Any]) -> str:
    """Fingerprint a security rule, path and source content without exposing matches.

    Args:
        result: Result supplied by the caller.

    Returns:
        Text representation produced by the documented operation.
    """
    value = "\0".join((result["check_id"], result["path"], result["extra"]["lines"]))
    return hashlib.sha256(value.encode()).hexdigest()


def check_report(report: dict[str, Any], baseline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reject scan errors or findings absent from the reviewed security baseline.

    Args:
        report: Measured quality or security report to validate.
        baseline: Previously reviewed measured values or finding fingerprints.

    Returns:
        New findings or scanner errors that must block the security gate.

    Raises:
        ValueError: Security scan omitted the Validator.
    """
    if report["errors"]:
        raise ValueError("Security scanner reported errors")
    scanned = set(report["paths"]["scanned"])
    if not {"app/services/validation.py", "app/models/validation.py"} <= scanned:
        raise ValueError("Security scan omitted the Validator")
    known = {entry["fingerprint"] for entry in baseline}
    return [
        {"rule": result["check_id"], "file": result["path"], "line": result["start"]["line"]}
        for result in report["results"]
        if finding_fingerprint(result) not in known
    ]


def main(argv: list[str] | None = None) -> int:
    """Run the security gate command with validated arguments and explicit outcomes.

    Args:
        argv: Optional CLI arguments; None uses the process command line.

    Returns:
        int value produced by this operation.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    baseline_path = Path(__file__).with_name("security_baseline.json")
    logger = structlog.get_logger()
    try:
        report = json.loads(args.report.read_text())
        findings = check_report(report, json.loads(baseline_path.read_text()))
        for finding in findings:
            logger.error("new_security_finding", **finding)
        logger.info(
            "security_checked", existing=len(report["results"]) - len(findings), new=len(findings)
        )
        return int(bool(findings))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        logger.error("security_check_failed", error_type=type(exc).__name__)
        return 2


if __name__ == "__main__":
    configure_logging("INFO")
    raise SystemExit(main())
