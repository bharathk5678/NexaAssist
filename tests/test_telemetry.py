from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from app.core import observability


def run_instrumented(script: str, *, llmobs_enabled: bool = False) -> list[dict[str, Any]]:
    result = subprocess.run(
        [str(Path(sys.executable).with_name("ddtrace-run")), sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env={
            **os.environ,
            "DD_TRACE_ENABLED": "true",
            "DD_APM_TRACING_ENABLED": str(not llmobs_enabled).lower(),
            "DD_SERVICE": "nexaassist-test",
            "DD_ENV": "test",
            "DD_VERSION": "test-version",
            "DD_LOGS_INJECTION": "true",
            "DD_LLMOBS_ENABLED": str(llmobs_enabled).lower(),
            "DD_LLMOBS_AGENTLESS_ENABLED": "false",
            "DD_RUNTIME_METRICS_ENABLED": "false",
            "DD_INSTRUMENTATION_TELEMETRY_ENABLED": "false",
            "DD_REMOTE_CONFIGURATION_ENABLED": "false",
            "DD_TRACE_STARTUP_LOGS": "false",
        },
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert "failed to enable ddtrace support for pymongo" not in result.stderr
    return [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]


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
    records = run_instrumented(script)
    log = next(record for record in records if record.get("event") == "correlated_log")
    assert log["dd.trace_id"] != "0"
    assert log["dd.span_id"] != "0"
    assert log["dd.service"] == "nexaassist-test"
    assert log["dd.env"] == "test"
    assert log["dd.version"] == "test-version"
    spans = next(record["spans"] for record in records if "spans" in record)
    assert any(
        span["name"] == "fastapi.request"
        and span["resource"] == "POST /answer"
        and span["service"] == "nexaassist-test"
        and span["span_kind"] == "server"
        and span["http_status"] == "422"
        for span in spans
    )
    assert any(
        span["name"] == "fastapi.request"
        and span["resource"] == "GET /health"
        and span["service"] == "nexaassist-test"
        and span["span_kind"] == "server"
        for span in spans
    )


def test_versioned_prompts_reach_llm_spans_and_remain_scoped() -> None:
    script = """
import asyncio
import json
from unittest.mock import patch
import httpx
from ddtrace.llmobs import LLMObs
from ddtrace.trace import tracer
from langchain_openai import ChatOpenAI
from app.chains.prompts.answer import ANSWER_PROMPT, ANSWER_PROMPT_ID, ANSWER_PROMPT_VERSION
from app.chains.prompts.judge import JUDGE_PROMPT, JUDGE_PROMPT_ID, JUDGE_VERSION
from app.core.observability import prompt_annotation_context

events = []
def provider(request):
    return httpx.Response(200, json={
        "id": "resp_test", "object": "response", "created_at": 1,
        "model": "test-model", "status": "completed",
        "output": [{"id": "msg_test", "type": "message", "role": "assistant",
                    "status": "completed", "content": [{"type": "output_text",
                    "text": "synthetic test answer", "annotations": []}]}],
        "usage": {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13}
    })
client = httpx.AsyncClient(transport=httpx.MockTransport(provider))
model = ChatOpenAI(model="test-model", api_key="test", use_responses_api=True,
                   http_async_client=client, base_url="https://unit.test/v1")

async def answer(query):
    variables = dict(query=query, as_of="2026-10-01", product_id="NEXA-HL",
                     context='[{"policy": "synthetic {braces}"}]', citation_feedback="")
    with prompt_annotation_context(ANSWER_PROMPT, variables,
                                  prompt_id=ANSWER_PROMPT_ID, version=ANSWER_PROMPT_VERSION):
        await (ANSWER_PROMPT | model).ainvoke(variables)

async def main():
    await asyncio.gather(answer("first question"), answer("second question"))
    variables = {"record": '{"response": "synthetic"}'}
    with prompt_annotation_context(JUDGE_PROMPT, variables,
                                  prompt_id=JUDGE_PROMPT_ID, version=JUDGE_VERSION):
        await (JUDGE_PROMPT | model).ainvoke(variables)
    try:
        with prompt_annotation_context(JUDGE_PROMPT, variables,
                                      prompt_id=JUDGE_PROMPT_ID, version=JUDGE_VERSION):
            await (JUDGE_PROMPT | model).ainvoke({})
    except KeyError:
        pass
    with LLMObs.llm(model_name="test", name="unrelated"):
        pass
    await client.aclose()

# Capture serialized SDK events before export; no Agent or provider is contacted.
with patch("ddtrace.llmobs._writer.LLMObsSpanWriter.enqueue",
           lambda self, event: events.append(event)):
    asyncio.run(main())
    LLMObs.flush()
print(json.dumps({"events": events}))
LLMObs.disable()
tracer.shutdown()
"""
    events = run_instrumented(script, llmobs_enabled=True)[-1]["events"]
    llm_events = [event for event in events if event["meta"]["span"]["kind"] == "llm"]
    prompts = [
        event["meta"]["input"]["prompt"] for event in llm_events if event["name"] != "unrelated"
    ]
    # OpenAI provider calls are the LLM spans; LangChain wrappers are workflows.
    assert len(prompts) == 3
    answers = [prompt for prompt in prompts if prompt["id"] == "nexaassist-policy-answer"]
    assert {prompt["variables"]["query"] for prompt in answers} == {
        "first question",
        "second question",
    }
    assert all(prompt["version"] == "1.0.0" for prompt in answers)
    assert all("{{query}}" in prompt["chat_template"][1]["content"] for prompt in answers)
    assert all(
        "synthetic {braces}" not in prompt["chat_template"][1]["content"] for prompt in answers
    )
    for event in llm_events:
        prompt = event["meta"].get("input", {}).get("prompt", {})
        if prompt.get("id") == "nexaassist-policy-answer":
            assert prompt["variables"]["query"] in event["meta"]["input"]["messages"][-1]["content"]
    judge = next(prompt for prompt in prompts if prompt["id"] == "nexaassist-policy-judge")
    assert judge["version"] == "policy-judge-v2"
    assert set(judge["variables"]) == {"record"}
    unrelated = next(event for event in llm_events if event["name"] == "unrelated")
    assert "prompt" not in unrelated["meta"].get("input", {})


def test_disabled_prompt_tracking_does_not_render_or_annotate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = Mock()
    datadog = Mock(enabled=False)
    monkeypatch.setattr(observability, "LLMObs", datadog)
    with observability.prompt_annotation_context(prompt, {}, prompt_id="test", version="1"):
        pass
    prompt.format_messages.assert_not_called()
    datadog.annotation_context.assert_not_called()


def test_api_workflows_keep_api_identity_when_ui_propagates_its_llm_application() -> None:
    script = """
import asyncio
import json
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch
from ddtrace.llmobs import LLMObs
from ddtrace.trace import tracer
from langchain_core.runnables import RunnableLambda
from app.core.config import Settings
from app.models.answer import AnswerResponse
from app.models.evaluation import METRIC_NAMES, EvaluatedAnswerRequest, QualityScore
from app.models.retrieval import RetrieveRequest, RetrieveResponse
from app.services import answer as answers, evaluation

settings = Settings(_env_file=None, mongodb_uri="mongodb://unused", mongodb_db="unused",
                    mongodb_collection="unused", openai_api_key="unused",
                    institution="NexaBank", jurisdiction="IN", confidentiality_level="internal",
                    dd_service="nexaassist-api")
evidence = RetrieveResponse(as_of="2026-10-01", results=[],
                           timings=dict(search_ms=0, parent_ms=0, total_ms=0))
answer = AnswerResponse(as_of=evidence.as_of, status="insufficient_evidence",
                        answer="No evidence", citations=[], retrieval_timings=evidence.timings,
                        generation_ms=0)
metrics = {name: QualityScore(status="unavailable", reason="No evidence") for name in METRIC_NAMES}
events = []

async def requests(headers):
    LLMObs.activate_distributed_headers(headers)
    with LLMObs.workflow(name="inherited_control"):
        pass
    for function, request_type in ((answers.answer_policy, RetrieveRequest),
                                   (evaluation.answer_with_quality, EvaluatedAnswerRequest)):
        LLMObs.activate_distributed_headers(headers)
        result = await function(request_type(query="limit", as_of="2026-10-01"), settings)
        assert result is not None

with ExitStack() as stack:
    stack.enter_context(patch("ddtrace.llmobs._writer.LLMObsSpanWriter.enqueue",
                             lambda self, event: events.append(event)))
    for service in (answers, evaluation):
        stack.enter_context(patch.object(service, "get_chat_model", return_value=object()))
        stack.enter_context(patch.object(service, "build_answer_chain",
                                        return_value=RunnableLambda(lambda _: answer)))
    stack.enter_context(patch.object(evaluation, "retrieve_policy", AsyncMock(return_value=evidence)))
    stack.enter_context(patch.object(evaluation, "score_answer", AsyncMock(return_value=metrics)))
    with LLMObs.workflow(name="ui", agent_service="nexaassist-ui"):
        headers = LLMObs.inject_distributed_headers({})
    asyncio.run(requests(headers))
    LLMObs.flush()
print(json.dumps({"events": events}))
LLMObs.disable()
tracer.shutdown()
"""
    events = run_instrumented(script, llmobs_enabled=True)[-1]["events"]
    workflows = {
        event["name"]: event
        for event in events
        if event["name"] in {"policy_answer", "policy_answer_live_evaluation"}
    }
    assert set(workflows) == {"policy_answer", "policy_answer_live_evaluation"}
    assert all("ml_app:nexaassist-api" in event["tags"] for event in workflows.values())
    inherited = next(event for event in events if event["name"] == "inherited_control")
    assert "ml_app:nexaassist-ui" in inherited["tags"]
    ui = next(event for event in events if event["name"] == "ui")
    assert all(
        event["_dd"]["apm_trace_id"] == ui["_dd"]["apm_trace_id"] for event in workflows.values()
    )
