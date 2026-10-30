# Constraints

Last reviewed: 2026-10-27. Scope: application code, tests and their configuration.
The user selected coverage and source/secret security scanning, blocking checks,
measured baselines that must not regress, and about 90 seconds for routine local
checks. Full CI checks may run longer. Existing work must be preserved.

## Floor

- No new checker-suppression comments, skipped tests, unimplemented stubs or empty exception handlers.
- No deleted tests or removed assertions without an explicitly reviewed reason.
- No secrets in source. Scanner output must identify the rule and location without printing matched values.
- Do not weaken this file, expand the security baseline or silence a check to make a change pass.

The diff guard adapts the constraint-driven-development skill's floor-guard
reference to Python. It inspects the base-to-working-tree diff, staged changes
and untracked Python files. Documentation quoting a pattern is not executable
code. Exit 0 means clean, 1 means a violation, and 2 means the guard could not run.

## Enforced with numbers

| Dimension | Rule | Checked by | Runs at |
| --- | --- | --- | --- |
| Floor | 0 unreviewed violations | `uv run --locked --no-sync python -m app.evaluation.floor_guard --base HEAD` | fast; CI uses the PR base |
| Lint and formatting | 0 errors | `uv run --locked --no-sync ruff check app tests` and `uv run --locked --no-sync ruff format --check app tests` | fast |
| Types | 0 errors in app and changed tests | `uv run --locked --no-sync mypy app tests` | fast |
| Application line coverage | >= 84.13% | `make check-task` runs pytest-cov with `--cov=app --cov-fail-under=84.13` | task end; CI |
| Changed application lines | >= 100% | `uv run --locked --no-sync diff-cover app/evaluation/reports/coverage.xml --compare-branch HEAD --include-untracked --include 'app/**' --fail-under 100` | task end; CI uses the PR base |
| Source and secret security | 0 new ERROR-severity fingerprints; no scan errors | `make check-full` runs Semgrep CE 1.182.1 with `p/default`, `p/owasp-top-ten`, `p/secrets`, then `app.evaluation.security_gate` | full local check; CI |
| Scored Phase 1 release quality | Complete ten-case dataset, correct statuses, all finite metrics, unchanged protocol, no regression in four RAGAS and two judge means | `make check-ai` and `app.evaluation.phase_gate`; measured dense and hybrid/rerank baselines in `evaluation/datasets/phase1_*_baseline.json` | explicit approved live check; trusted release workflow |

Coverage initially measured 79.70% application and 97.92% changed lines. After
the extension, the passing targets were ratcheted up to 81.45% and 100%,
respectively, rather than an invented percentage. The application threshold is
rounded down to two decimals; the changed-line value is exact. Both baselines must hold;
the same test run writes the coverage report used by diff-cover. Untracked
application files are included. There is no small-diff bypass or coverage
omission added for this change.

On 27 October the integrated four-agent suite measured 2397/2849 application
lines (84.13% displayed), so the application floor was ratcheted to 84.13%.
Changed-line coverage remains exactly 100%. The same coverage report verifies
both gates; no second measurement or exclusion is used to raise the floor.

Security is an external rule check, independent of project assertions. Seven
pre-existing ERROR findings were measured: one `missing-user` in app/Dockerfile
and six `react-insecure-request` findings in prior browser-test artifacts under
app/evaluation/results/system_uat_20261021. Exact rule/path/content fingerprints
are retained in app/evaluation/security_baseline.json; merely keeping the same
count cannot hide a replacement finding. Removing findings tightens the bar.
This baseline is not a claim that the seven findings are safe or remediated.
Semgrep suppression comments are disabled, metrics are off, and raw finding
JSON stays in ignored local reports. New secret findings always block.

## Lifecycle

`make check-fast` runs the floor, Ruff and full application/test mypy. `make check-task` adds the
single coverage-enabled pytest run and diff coverage. `make check-full` adds
source/secret security scanning. `BASE_REF` selects the comparison reference;
it defaults to HEAD locally and is the PR base SHA in CI. The wrappers must
mirror this file, which remains the canonical contract. No commit, push or
branch-protection change is implied by running checks.

Routine checks target 90 seconds on the development machine. Network rule
downloads and full CI security scanning are outside the edit loop. A missing
tool, failed rule download or unreadable report is a failed check, never a pass.

## Measured, not yet enforced

| Metric | Recorded value | Direction |
| --- | --- | --- |
| Pre-extension root test suite | 227 passed, 14.09 seconds with coverage | Preserve all existing cases; add relevant regression cases |
| Extension verification | 311 passed, 15.55 seconds with coverage | Preserve the additional regression cases |
| Full test-tree mypy | Existing optional `await_args` issue in tests/test_amendments.py:107 | Keep visible; do not add suppressions or new type errors |
| Live integration behavior | Not measured | Requires separately configured model, RAG/Atlas, bank and telemetry integrations |

Dependency vulnerability auditing, UI performance, accessibility and additional
architecture tooling are not enabled by this contract. Existing AGENTS.md layer
rules still apply. The security gate covers source and secret rules, not a
dependency vulnerability database.

The container's missing-user finding was remediated with a non-root runtime and
verified by Semgrep. Its fingerprint was removed from the baseline, leaving the
six original browser-artifact findings. No new finding was added to the baseline.

The four-agent integration corrected the previously recorded optional-await_args
typing issue. The type command now includes the complete test tree, including all
new workflow tests. This strengthens the existing zero-error requirement.

## Exceptions

No new exceptions were approved. Any future exception needs a rule, exact path,
reason, owner and expiry; adding it requires explicit review.

The user requested a fresh full-dataset AI baseline on 27 October. Both dense and
hybrid/rerank protocols were measured separately; their model/protocol and dataset
digests cannot silently be interchanged. These live calls require approved data,
provider credentials and a reachable corpus/reranker. They stay outside the
90-second local edit loop. The gate blocks incomplete, invalid or regressed
reports; it never replaces missing live scores with mocked or historical passes.
Capturing a new baseline is an explicit, non-overwriting operation, not a way for
the agent to lower an existing floor after a failed check.
