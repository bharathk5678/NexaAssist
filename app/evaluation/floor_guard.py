"""Inspect diffs for weakened checks, removed assertions and unfinished work."""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import subprocess
import tokenize
from pathlib import Path

import structlog

from app.core.logging import configure_logging

# Adapted from constraint-driven-development/references/floor-guard.md.
Finding = tuple[str, int, str]
SUPPRESSIONS = re.compile(
    r"noqa|type:\s*ignore|nosemgrep|gitleaks:allow|coverage:\s*ignore|pragma:\s*no\s*(?:cover|branch)",
    re.IGNORECASE,
)


def _expected_set(node: ast.AST) -> tuple[str, frozenset[str]] | None:
    if not isinstance(node, ast.Assert) or not isinstance(node.test, ast.Compare):
        return None
    comparison = node.test
    if len(comparison.ops) != 1 or not isinstance(comparison.ops[0], ast.Eq):
        return None
    expected = comparison.comparators[0]
    if not isinstance(expected, ast.Set) or not all(
        isinstance(item, ast.Constant) and isinstance(item.value, str) for item in expected.elts
    ):
        return None
    return ast.dump(comparison.left), frozenset(ast.literal_eval(expected))


def check_diff(diff: str, sources: dict[str, str]) -> list[Finding]:
    """Report new constraint bypasses, weakened checks and removed assertions in a diff.

    Args:
        diff: Unified source diff to inspect without weakening existing checks.
        sources: Numbered policy passages and citation metadata retained for generation.

    Returns:
        Path, line and rule triples for detected constraint violations.

    Raises:
        ValueError: Invalid diff hunk.
    """
    added: dict[str, set[int]] = {}
    additions: list[tuple[str, int, str]] = []
    removals: list[tuple[str, int, str]] = []
    findings: list[Finding] = []
    file, old_file, line, old_line, header = "", "", 0, 0, False
    for text in diff.splitlines():
        if text.startswith("diff "):
            header = True
        elif text.startswith("@@"):
            match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", text)
            if match is None:
                raise ValueError("Invalid diff hunk")
            old_line, line = map(int, match.groups())
            header = False
        elif header and text.startswith("--- "):
            old_file = text[4:].removeprefix("a/")
        elif header and text.startswith("+++ "):
            file = text[4:].removeprefix("b/")
            if file == "/dev/null":
                file = old_file
                if Path(file).name.startswith("test_"):
                    findings.append((file, 0, "test-deleted"))
        elif not header and text.startswith("+"):
            added.setdefault(file, set()).add(line)
            additions.append((file, line, text[1:]))
            line += 1
        elif not header and text.startswith("-"):
            removals.append((file, old_line, text[1:]))
            old_line += 1
        elif not header and text.startswith(" "):
            line += 1
            old_line += 1

    for file, lines in added.items():
        if not file.endswith(".py"):
            continue
        source = sources[file]
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT and token.start[0] in lines:
                if SUPPRESSIONS.search(token.string):
                    findings.append((file, token.start[0], "silenced-checker"))
                if re.search(r"\bTODO\b", token.string):
                    findings.append((file, token.start[0], "unfinished-work"))
        for node in ast.walk(ast.parse(source)):
            number = getattr(node, "lineno", 0)
            if number not in lines:
                continue
            if isinstance(node, ast.Pass) or (
                isinstance(node, ast.Raise)
                and isinstance(node.exc, (ast.Call, ast.Name))
                and ast.unparse(node.exc.func if isinstance(node.exc, ast.Call) else node.exc)
                == "NotImplementedError"
            ):
                findings.append((file, number, "unfinished-work"))
            if isinstance(node, ast.Attribute) and ast.unparse(node) in (
                "pytest.skip",
                "pytest.mark.skip",
                "pytest.mark.skipif",
                "pytest.mark.xfail",
            ):
                findings.append((file, number, "test-made-easier"))

    retained_sets = {
        file: [
            value
            for node in ast.walk(ast.parse(sources[file]))
            if getattr(node, "lineno", 0) in lines and (value := _expected_set(node)) is not None
        ]
        for file, lines in added.items()
        if file.endswith(".py")
    }
    for file, number, text in removals:
        if Path(file).name.startswith("test_") and re.search(r"\bassert\b|\.assert_", text):
            try:
                previous = _expected_set(ast.parse(text.strip()).body[0])
            except SyntaxError:
                previous = None
            # An expanded exact inventory retains its assertion and every previous required member.
            retained = previous is not None and any(
                target == previous[0] and previous[1] <= values
                for target, values in retained_sets.get(file, [])
            )
            if not retained:
                findings.append((file, number, "assertion-removed"))
        if file == "CONSTRAINTS.md" and text.startswith(("- ", "| ")):
            key = text.split("|")[1].strip() if text.startswith("|") else text.split(":")[0]
            replacement = next(
                (
                    value
                    for path, _, value in additions
                    if path == file
                    and (
                        value.split("|")[1].strip()
                        if value.startswith("|")
                        else value.split(":")[0]
                    )
                    == key
                ),
                None,
            )
            if replacement is None:
                findings.append((file, number, "rule-removed"))
            elif text != replacement:
                before = re.findall(r"(>=|<=)\s*(\d+(?:\.\d+)?)", text)
                after = re.findall(r"(>=|<=)\s*(\d+(?:\.\d+)?)", replacement)
                if (
                    len(after) < len(before)
                    or any(
                        direction != new_direction
                        or (
                            float(new) < float(old)
                            if direction == ">="
                            else float(new) > float(old)
                        )
                        for (direction, old), (new_direction, new) in zip(before, after)
                    )
                    or (not before and re.findall(r"\d+", text) != re.findall(r"\d+", replacement))
                ):
                    findings.append((file, number, "threshold-weakened-or-changed"))
    for file, number, text in additions:
        if file == "CONSTRAINTS.md" and re.match(r"\|\s*[WE]\d+\s*\|", text):
            findings.append((file, number, "new-exception"))
    return findings


def main(argv: list[str] | None = None) -> int:
    """Run the floor guard command with validated arguments and explicit outcomes.

    Args:
        argv: Optional CLI arguments; None uses the process command line.

    Returns:
        int value produced by this operation.

    Raises:
        ValueError: Unable to inspect untracked file.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="HEAD")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]

    def git(*values: str) -> str:
        """Read the requested repository state and fail explicitly if Git cannot inspect it.

        Args:
            values: Values supplied by the caller.

        Returns:
            Text representation produced by the documented operation.
        """
        return subprocess.run(
            ["git", *values], cwd=root, check=True, capture_output=True, text=True
        ).stdout

    try:
        base = git("merge-base", args.base, "HEAD").strip()
        diff = git("diff", "--no-ext-diff", "--unified=0", base, "--")
        for name in git("ls-files", "--others", "--exclude-standard", "-z").split("\0"):
            if name.endswith(".py") or name == "CONSTRAINTS.md":
                result = subprocess.run(
                    ["git", "diff", "--no-index", "--unified=0", "/dev/null", name],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode not in (0, 1):
                    raise ValueError("Unable to inspect untracked file")
                diff += "\n" + result.stdout
        sources = {
            path.relative_to(root).as_posix(): path.read_text()
            for directory in (root / "app", root / "tests")
            for path in directory.rglob("*.py")
        }
        findings = check_diff(diff, sources)
        baseline_path = "app/evaluation/security_baseline.json"
        if git("ls-tree", base, "--", baseline_path).strip():
            before = json.loads(git("show", f"{base}:{baseline_path}"))
            current = json.loads((root / baseline_path).read_text())
            if {item["fingerprint"] for item in current} - {item["fingerprint"] for item in before}:
                findings.append((baseline_path, 0, "security-baseline-expanded"))
        logger = structlog.get_logger()
        for file, line, rule in findings:
            logger.error("floor_violation", file=file, line=line, rule=rule)
        logger.info("floor_checked", violations=len(findings))
        return int(bool(findings))
    except (
        OSError,
        ValueError,
        KeyError,
        SyntaxError,
        tokenize.TokenError,
        subprocess.CalledProcessError,
    ) as exc:
        structlog.get_logger().error("floor_check_failed", error_type=type(exc).__name__)
        return 2


if __name__ == "__main__":
    configure_logging("INFO")
    raise SystemExit(main())
