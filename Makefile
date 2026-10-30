BASE_REF ?= HEAD
UV ?= uv
REPORTS = app/evaluation/reports
RUN = $(UV) run --locked --no-sync
AI_REPORT ?= app/evaluation/reports/phase1-current.json
AI_BASELINE ?= evaluation/datasets/phase1_dense_baseline.json

.PHONY: check-fast check-task check-full check-ai
check-fast:
	$(RUN) python -m app.evaluation.floor_guard --base "$(BASE_REF)"
	$(RUN) ruff check app tests
	$(RUN) ruff format --check app tests
	$(RUN) mypy app tests

check-task: check-fast
	mkdir -p $(REPORTS)
	$(RUN) pytest tests/ -q --cov=app --cov-fail-under=84.13 --cov-report=term:skip-covered --cov-report=xml:$(REPORTS)/coverage.xml
	$(RUN) diff-cover $(REPORTS)/coverage.xml --compare-branch "$(BASE_REF)" --include-untracked --include 'app/**' --fail-under 100 --total-percent-float

check-full: check-task
	SEMGREP_SETTINGS_FILE=$(REPORTS)/semgrep-settings.yml $(UV) tool run --python 3.13 --from semgrep==1.182.1 semgrep scan --config p/default --config p/owasp-top-ten --config p/secrets --metrics off --disable-version-check --disable-nosem --severity ERROR --strict --json --output $(REPORTS)/security.json app
	$(RUN) python -m app.evaluation.security_gate $(REPORTS)/security.json

# Live provider/Atlas calls: run explicitly with approved data and configured credentials.
check-ai:
	test -f "$(AI_BASELINE)"
	$(RUN) python -m app.evaluation.run --output "$(AI_REPORT)"
	$(RUN) python -m app.evaluation.phase_gate check --report "$(AI_REPORT)" --baseline "$(AI_BASELINE)"
