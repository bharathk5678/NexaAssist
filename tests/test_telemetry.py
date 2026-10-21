from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_early_datadog_instrumentation_traces_api_and_correlates_json_logs() -> None:
    script = """
import json
import structlog
from ddtrace.trace import TraceFilter, tracer
from fastapi.testclient import TestClient
from app.core.logging import configure_logging
from app.core.config import get_settings
from app.main import create_app

spans = []
class Capture(TraceFilter):
    def process_trace(self, trace):
        spans.extend({"name": span.name, "resource": span.resource,
                      "service": span.service,
                      "span_kind": span.get_tag("span.kind"),
                      "http_status": span.get_tag("http.status_code")} for span in trace)
        return None  # Consume the test spans without contacting an Agent.

tracer.configure(trace_processors=[Capture()])
configure_logging("INFO")
with tracer.trace("telemetry.probe"):
    structlog.get_logger().info("correlated_log")
app = create_app()
# The invalid request must exercise HTTP tracing without provider configuration or calls.
app.dependency_overrides[get_settings] = lambda: None
client = TestClient(app)
assert client.get("/health").status_code == 200
assert client.post("/answer", json={}).status_code == 422
tracer.flush()
print(json.dumps({"spans": spans}))
tracer.shutdown()
"""
    result = subprocess.run(
        [str(Path(sys.executable).with_name("ddtrace-run")), sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env={
            **os.environ,
            "DD_TRACE_ENABLED": "true",
            "DD_SERVICE": "nexaassist-test",
            "DD_ENV": "test",
            "DD_VERSION": "test-version",
            "DD_LOGS_INJECTION": "true",
            "DD_LLMOBS_ENABLED": "false",
            "DD_RUNTIME_METRICS_ENABLED": "false",
            "DD_INSTRUMENTATION_TELEMETRY_ENABLED": "false",
            "DD_REMOTE_CONFIGURATION_ENABLED": "false",
            "DD_TRACE_STARTUP_LOGS": "false",
            "LANGCHAIN_TRACING_V2": "false",
            "LANGSMITH_TRACING": "false",
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert "failed to enable ddtrace support for pymongo" not in result.stderr
    records = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
    log = next(record for record in records if record.get("event") == "correlated_log")
    assert log["dd.trace_id"] != "0"
    assert log["dd.span_id"] != "0"
    assert log["dd.service"] == "nexaassist-test"
    assert log["dd.env"] == "test"
    assert log["dd.version"] == "test-version"
    spans = next(record["spans"] for record in records if "spans" in record)
    assert any(
        span["name"] == "fastapi.request"
        and span["resource"] == "GET /health"
        and span["service"] == "nexaassist-test"
        and span["span_kind"] == "server"
        for span in spans
    )
    assert any(
        span["name"] == "fastapi.request"
        and span["resource"] == "POST /answer"
        and span["service"] == "nexaassist-test"
        and span["span_kind"] == "server"
        and span["http_status"] == "422"
        for span in spans
    )
