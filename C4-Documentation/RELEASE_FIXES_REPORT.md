# Release fixes: floor checker and dependency packaging

Verified 30 October 2026. These are the two follow-up phases authorized after the
[structural refactor](AGENT_REFACTOR_REPORT.md). They resolve that report's checker
crash and missing checkpoint-dependency declaration. No deployment was performed.

## Phase 1: repair the floor checker

The checker collected diffs for tracked and untracked Python files, including
documentation source copies, but loaded source text only from `app/` and `tests/`.
Looking up another added Python file therefore raised `KeyError`.

`app/evaluation/floor_guard.py` now loads existing Python files from Git's tracked
and untracked inventory. Deleted paths need no current source text. Missing or
invalid source still fails inspection; no archive directory or Python file was
excluded to make the check pass.

The regression also exposed a false pass: Git appends a tab delimiter to some diff
headers containing spaces. The checker interpreted that delimiter as part of the
filename and silently skipped the source. The parser now removes the delimiter
and decodes Git's C-quoted UTF-8 paths before applying its existing checks.

Eighteen isolated Git-repository regression cases cover tracked/untracked files,
spaces/Unicode/tab characters, and all three outcomes:

- Clean source returns 0.
- A checker-suppression comment returns 1.
- Invalid Python returns 2; it is never reported as clean.

All existing assertions and constraint thresholds remain. Phase 1 is committed as
`54786ac` and passed `make check-task BASE_REF=de35ff9` before Phase 2 began.

## Phase 2: complete runtime dependency packaging

`requirements.txt` now declares:

```text
langgraph-checkpoint-mongodb>=0.4,<0.5
```

This matches the integration and version range already declared in
`pyproject.toml`. No dependency, model, API contract, environment secret or lockfile
was otherwise changed.

A fresh temporary Python environment was created outside the repository. Installing
only `requirements.txt` and running `uv pip check` succeeded. Verification then:

1. Confirmed every direct runtime dependency in `pyproject.toml` is declared by
   the compatibility requirements file.
2. Imported the MongoDB checkpoint integration and round-tripped a typed
   `AgentRequest` with nested `ServiceRequestDetails`.
3. Started both RAG and Agent application lifespans and received HTTP 200 from
   each `/health` endpoint through isolated in-process HTTP clients.

The clean environment resolved checkpoint integration 0.4.0 and PyMongo 4.16.0,
both within the existing declared ranges. The project's existing environment was
not upgraded. This verifies the requirements installation path; reproducible
deployment should continue to use the reviewed locked `uv` installation path.

## Final verification

`make check-full BASE_REF=de35ff9` completed successfully, including the prescribed
changed-line coverage command and pinned Semgrep scan.

| Check | Result |
|---|---|
| Floor guard | 0 violations; no crash |
| Application tests | 580 passed |
| Banking API/OpenAPI contract tests, run separately | 22 passed |
| Application coverage | 85.65%, above the unchanged 84.13% floor |
| Changed-line coverage | 8 executable lines, 0 missing, 100% |
| Ruff lint and formatting | Pass |
| mypy | Pass |
| Semgrep/security gate | 0 new ERROR findings; 6 reviewed existing findings; 0 scan errors |
| Fresh requirements-only install and dependency check | Pass |
| Fresh API startup and typed checkpoint serialization | Pass |

[Machine-readable verification](release-fixes-verification-20261030.json) records
the phase results. The earlier structural report remains historical evidence;
its two identified follow-up blockers are now resolved.

## Scope and remaining risks

- Constraints, CI workflows, `pyproject.toml`, `uv.lock` and `.env.example` retain
  their original contents. No new suppression, skipped test or relaxed threshold
  was introduced.
- No live banking operation, provider evaluation, deployment or push was performed.
- The six reviewed security findings remain visible; a passing no-new-findings
  gate is not a claim that those findings are safe or remediated.
- Local health/startup and isolated integration tests do not establish production
  load capacity, disaster recovery, enterprise identity or live integration quality.
- Both phase commits use Pankaj as author and committer, with no co-author trailers.
