"""Regression tests for constraints."""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from app.evaluation import floor_guard, security_gate


def patch(added: str, removed: str = "", file: str = "app/example.py") -> str:
    """Provide patch for the constraints scenario.

    Args:
        added: Added fixture or parametrized input for this scenario.
        removed: Removed fixture or parametrized input for this scenario.
        file: File fixture or parametrized input for this scenario.

    Returns:
        Text representation produced by the documented operation.
    """
    return (
        f"diff --git a/{file} b/{file}\n--- a/{file}\n+++ b/{file}\n"
        f"@@ -1,{len(removed.splitlines())} +1,{len(added.splitlines())} @@\n"
        + "".join(f"-{line}\n" for line in removed.splitlines())
        + "".join(f"+{line}\n" for line in added.splitlines())
    )


@pytest.mark.parametrize(
    "source,rule",
    [
        ("value = 1  # noqa: F841", "silenced-checker"),
        ("value = 1  # NOQA", "silenced-checker"),
        ("value = 1  # pragma: no cover", "silenced-checker"),
        ("# TODO: implement validation", "unfinished-work"),
        ("def run():\n    pass", "unfinished-work"),
        ("raise NotImplementedError('unfinished')", "unfinished-work"),
        ("raise NotImplementedError", "unfinished-work"),
        ("@pytest.mark.skip\ndef test_example():\n    assert True", "test-made-easier"),
        ("pytest.skip('later')", "test-made-easier"),
    ],
)
def test_floor_detects_added_bypasses(source: str, rule: str) -> None:
    """Verify floor detects added bypasses.

    Args:
        source: Source fixture or parametrized input for this scenario.
        rule: Rule fixture or parametrized input for this scenario.
    """
    result = floor_guard.check_diff(patch(source), {"app/example.py": source})
    assert any(finding[2] == rule for finding in result)


def test_floor_ignores_examples_and_unchanged_comments() -> None:
    """Verify floor ignores examples and unchanged comments."""
    source = 'example = "# noqa: example only"\n# noqa: existing\nvalue = 1'
    diff = patch('example = "# noqa: example only"')
    assert floor_guard.check_diff(diff, {"app/example.py": source}) == []


def test_floor_preserves_line_numbers_with_diff_context() -> None:
    """Verify floor preserves line numbers with diff context."""
    source = "first = 1\nsecond = 2\nlast = 3  # noqa"
    diff = (
        "diff --git a/app/example.py b/app/example.py\n--- a/app/example.py\n"
        "+++ b/app/example.py\n@@ -1,2 +1,3 @@\n first = 1\n second = 2\n+last = 3  # noqa\n"
    )
    assert floor_guard.check_diff(diff, {"app/example.py": source}) == [
        ("app/example.py", 3, "silenced-checker")
    ]


def test_floor_catches_deleted_tests_and_assertions() -> None:
    """Verify floor catches deleted tests and assertions."""
    diff = patch("value = 1", "assert value == 1", "tests/test_example.py")
    assert ("tests/test_example.py", 1, "assertion-removed") in floor_guard.check_diff(
        diff, {"tests/test_example.py": "value = 1"}
    )
    deleted = "diff --git a/tests/test_old.py b/tests/test_old.py\n--- a/tests/test_old.py\n+++ /dev/null\n"
    assert floor_guard.check_diff(deleted, {}) == [("tests/test_old.py", 0, "test-deleted")]


@pytest.mark.parametrize(
    "replacement,blocked",
    [
        ('assert paths == {"/agent", "/agent/runs"}', False),
        ('assert paths == {"/agent"}', False),
        ('assert paths == {"/other"}', True),
        ('assert other == {"/agent", "/agent/runs"}', True),
        ('assert paths != {"/agent"}', True),
        ("assert paths == paths", True),
        ("assert True", True),
        ("assert paths == {1}", True),
    ],
)
def test_floor_retains_exact_inventory_assertions_without_losing_members(
    replacement: str, blocked: bool
) -> None:
    """Verify floor retains exact inventory assertions without losing members.

    Args:
        replacement: Replacement fixture or parametrized input for this scenario.
        blocked: Blocked fixture or parametrized input for this scenario.
    """
    name = "tests/test_example.py"
    findings = floor_guard.check_diff(
        patch(replacement, 'assert paths == {"/agent"}', name), {name: replacement}
    )
    assert bool(findings) is blocked


@pytest.mark.parametrize(
    "old,new,blocked",
    [
        ("| Coverage | >= 79.70% |", "| Coverage | >= 79.69% |", True),
        ("| Coverage | >= 79.70% |", "| Coverage | >= 80.00% |", False),
        ("| Latency | <= 90 seconds |", "| Latency | <= 91 seconds |", True),
        ("| Latency | <= 90 seconds |", "| Latency | <= 89 seconds |", False),
        ("| Coverage | >= 79.70% |", "| Coverage | measured only |", True),
        ("| Types | 0 errors |", "| Types | 1 error |", True),
        ("- No skipped tests", "", True),
        ("", "| E1 | Coverage | tests | later | owner | 2026-11-01 |", True),
    ],
)
def test_floor_ratchet(old: str, new: str, blocked: bool) -> None:
    """Verify floor ratchet.

    Args:
        old: Old fixture or parametrized input for this scenario.
        new: New fixture or parametrized input for this scenario.
        blocked: Blocked fixture or parametrized input for this scenario.
    """
    findings = floor_guard.check_diff(patch(new, old, "CONSTRAINTS.md"), {})
    assert bool(findings) == blocked


def test_floor_fails_on_an_invalid_hunk() -> None:
    """Verify floor fails on an invalid hunk."""
    with pytest.raises(ValueError, match="Invalid diff hunk"):
        floor_guard.check_diff("@@ invalid", {})


def test_floor_command_success_failure_and_baseline_expansion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify floor command success failure and baseline expansion.

    Args:
        tmp_path: Isolated temporary directory for this test's files.
        monkeypatch: Pytest fixture used to isolate dependencies for this scenario.
    """
    evaluation = tmp_path / "app" / "evaluation"
    evaluation.mkdir(parents=True)
    baseline = evaluation / "security_baseline.json"
    baseline.write_text("[]")
    monkeypatch.setattr(floor_guard, "__file__", str(evaluation / "floor_guard.py"))
    untracked_code = 1

    def git(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        command = args[1]
        stdout = "base" if command == "merge-base" else "[]" if command == "show" else ""
        if command == "ls-tree":
            stdout = "tracked security baseline"
        if command == "ls-files":
            stdout = "app/example.py\0"
        if command == "diff" and "--no-index" in args:
            return subprocess.CompletedProcess(args, untracked_code, patch("value = 1"), "")
        return subprocess.CompletedProcess(args, 0, stdout, "")

    (tmp_path / "app" / "example.py").write_text("value = 1")
    monkeypatch.setattr(floor_guard.subprocess, "run", git)
    assert floor_guard.main([]) == 0
    untracked_code = 2
    assert floor_guard.main([]) == 2
    untracked_code = 1
    baseline.write_text('[{"fingerprint":"new"}]')
    assert floor_guard.main([]) == 1

    def failure(*args: object, **kwargs: object) -> None:
        raise OSError("private detail")

    monkeypatch.setattr(floor_guard.subprocess, "run", failure)
    assert floor_guard.main([]) == 2


def report() -> dict:
    """Provide report for the constraints scenario.

    Returns:
        Named values describing the documented operation or diagnostic outcome.
    """
    return {
        "errors": [],
        "paths": {"scanned": ["app/services/validation.py", "app/models/validation.py"]},
        "results": [
            {
                "check_id": "example-rule",
                "path": "app/example.py",
                "start": {"line": 2},
                "extra": {"lines": "sensitive-example-value"},
            }
        ],
    }


def test_security_gate_freezes_content_and_never_logs_matches(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify security gate freezes content and never logs matches.

    Args:
        tmp_path: Isolated temporary directory for this test's files.
        capsys: Pytest fixture capturing output without exposing live credentials.
        monkeypatch: Pytest fixture used to isolate dependencies for this scenario.
    """
    data = report()
    baseline = [{"fingerprint": security_gate.finding_fingerprint(data["results"][0])}]
    assert security_gate.check_report(data, baseline) == []
    data["results"][0]["extra"]["lines"] = "changed-sensitive-value"
    assert security_gate.check_report(data, baseline) == [
        {"rule": "example-rule", "file": "app/example.py", "line": 2}
    ]
    monkeypatch.setattr(security_gate, "__file__", str(tmp_path / "security_gate.py"))
    (tmp_path / "security_baseline.json").write_text(json.dumps(baseline))
    path = tmp_path / "report.json"
    path.write_text(json.dumps(data))
    assert security_gate.main([str(path)]) == 1
    assert "changed-sensitive-value" not in capsys.readouterr().out
    data["results"] = []
    path.write_text(json.dumps(data))
    assert security_gate.main([str(path)]) == 0
    path.write_text("invalid")
    assert security_gate.main([str(path)]) == 2


@pytest.mark.parametrize("failure", ["scan_error", "omitted_validator"])
def test_security_gate_rejects_incomplete_scans(failure: str) -> None:
    """Verify security gate rejects incomplete scans.

    Args:
        failure: Failure mode selected by the parametrized test.
    """
    data = report()
    if failure == "scan_error":
        data["errors"] = [{"type": "parse error"}]
    else:
        data["paths"]["scanned"] = []
    with pytest.raises(ValueError):
        security_gate.check_report(data, [])


@pytest.mark.parametrize("valid", [True, False])
def test_security_cli_returns_real_process_exit_codes(
    valid: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify security cli returns real process exit codes.

    Args:
        valid: Valid fixture or parametrized input for this scenario.
        tmp_path: Isolated temporary directory for this test's files.
        monkeypatch: Pytest fixture used to isolate dependencies for this scenario.
    """
    data = report()
    data["results"] = []
    path = tmp_path / "report.json"
    path.write_text(json.dumps(data) if valid else "invalid")
    monkeypatch.setattr(sys, "argv", ["security_gate", str(path)])
    with pytest.raises(SystemExit) as result:
        runpy.run_path(security_gate.__file__, run_name="__main__")
    assert result.value.code == (0 if valid else 2)


@pytest.mark.parametrize("valid", [True, False])
def test_floor_cli_returns_real_process_exit_codes(
    valid: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify floor cli returns real process exit codes.

    Args:
        valid: Valid fixture or parametrized input for this scenario.
        monkeypatch: Pytest fixture used to isolate dependencies for this scenario.
    """
    monkeypatch.setattr(sys, "argv", ["floor_guard", "--base", "HEAD" if valid else "missing-ref"])
    with pytest.raises(SystemExit) as result:
        runpy.run_path(floor_guard.__file__, run_name="__main__")
    assert result.value.code == (0 if valid else 2)


def test_floor_does_not_lose_a_multiline_assertion() -> None:
    """Verify floor does not lose a multiline assertion."""
    file = "tests/test_example.py"
    assert floor_guard.check_diff(patch("value = 1", "assert (", file), {file: "value = 1"}) == [
        (file, 1, "assertion-removed")
    ]


@pytest.mark.parametrize("tracked", [False, True])
@pytest.mark.parametrize(
    "relative",
    ["saved sources/example.py", "saved sources/examplé.py", "saved\tsources/example.py"],
)
@pytest.mark.parametrize(
    ("source", "expected_exit"),
    [("value = 2\n", 0), ("value = 2  # noqa: F841\n", 1), ("def broken(\n", 2)],
)
def test_floor_inspects_python_outside_application_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tracked: bool,
    relative: str,
    source: str,
    expected_exit: int,
) -> None:
    """Inspect external tracked/untracked sources without hiding violations or scan errors.

    Args:
        tmp_path: Isolated Git repository for the command-level regression.
        monkeypatch: Redirects the checker to the isolated repository.
        tracked: Whether the source exists in the committed baseline.
        relative: Filename exercising Git's spaces, Unicode or control-character quoting.
        source: Current clean, suppressed or invalid Python source.
        expected_exit: Required clean, violation or inspection-failure exit code.
    """
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True, capture_output=True)
    path = tmp_path / "C4-Documentation" / relative
    path.parent.mkdir(parents=True)
    if tracked:
        path.write_text("value = 1\n")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Pankaj",
            "-c",
            "user.email=fixture@localhost",
            "commit",
            "--quiet",
            "--allow-empty",
            "-m",
            "Test baseline",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    path.write_text(source)
    monkeypatch.setattr(
        floor_guard, "__file__", str(tmp_path / "app" / "evaluation" / "floor_guard.py")
    )
    assert floor_guard.main(["--base", "HEAD"]) == expected_exit
