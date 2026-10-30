"""Regression tests for agent ui."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import get_args
from uuid import uuid4

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from app.models.agent_run import AgentRunResponse
from app.models.validation import ServiceRequestType
from app.ui import app as ui


@pytest.fixture
def run_view() -> dict:
    """Provide run view for the agent ui scenario.

    Returns:
        Named values describing the documented operation or diagnostic outcome.
    """
    now = datetime.now(UTC)
    return {
        "run_id": str(uuid4()),
        "status": "pending_approval",
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=15)).isoformat(),
        "proposal_hash": "a" * 64,
        "response": {
            "intent": "supported_action",
            "status": "validated",
            "message": "Review required",
            "validation": {
                "decision": "allowed",
                "reason": "Permitted by policy",
                "proposal": {"customer_id": "NXC-0010", "request_type": "CALLBACK"},
                "evidence": [
                    {
                        "quote": "Callback requests are permitted.",
                        "citation": {
                            "doc_id": "POL-OPS-001",
                            "title": "Scope",
                            "policy_version": "1.0",
                            "clause": "5.1",
                            "effective_date": "2025-01-01",
                        },
                    }
                ],
            },
        },
    }


@pytest.fixture
def screen(monkeypatch: pytest.MonkeyPatch, run_view: dict):
    """Provide screen for the agent ui scenario.

    Args:
        monkeypatch: Pytest fixture used to isolate dependencies for this scenario.
        run_view: Synthetic saved-run response used by the UI test.

    Yields:
        Each fixture value or stored key produced by this operation.
    """
    calls: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=run_view)

    with httpx.Client(
        base_url="http://agent.test", transport=httpx.MockTransport(respond)
    ) as client:
        monkeypatch.setattr(ui, "api_client", lambda _: client)
        app = AppTest.from_file(Path("app/streamlit_app.py").resolve(), default_timeout=10)
        app.session_state["workspace"] = "Service requests"
        app.run()
        app.text_input(key="agent_token").set_value("owner-test-credential").run()
        assert not app.exception
        yield app, calls


@pytest.mark.parametrize("kind", get_args(ServiceRequestType.__value__))
def test_start_uses_shared_schema_and_preserves_saved_run(screen, kind: str) -> None:
    """Verify start uses shared schema and preserves saved run.

    Args:
        screen: Streamlit test application and recorded HTTP calls.
        kind: Service-request or response type selected for this scenario.
    """
    app, calls = screen
    app.text_input(key="agent_customer").set_value("NXC-0010")
    app.selectbox(key="agent_kind").select(kind)
    app.text_input[2].set_value("NXL-0010")
    next(b for b in app.button if b.label == "Prepare for approval").click().run()
    assert not app.exception
    assert len(calls) == 1
    assert calls[0].url.path == "/agent/runs"
    body = json.loads(calls[0].content)
    assert body["action_details"]["request_type"] == kind
    assert body["action_details"]["loan_account_id"] == "NXL-0010"
    assert body["customer_id"] == "NXC-0010" and body["as_of"]
    assert calls[0].headers["Authorization"] == "Bearer owner-test-credential"
    assert app.text_input(key="agent_run_id").value
    assert app.json


def load_run(app: AppTest, run_view: dict) -> None:
    """Provide load run for the agent ui scenario.

    Args:
        app: App fixture or parametrized input for this scenario.
        run_view: Synthetic saved-run response used by the UI test.
    """
    app.text_input(key="agent_run_id").set_value(run_view["run_id"])
    next(b for b in app.button if b.label == "Load saved run").click().run()
    assert not app.exception


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_reviewer_posts_loaded_hash_only_after_confirmation(
    screen, run_view: dict, decision: str
) -> None:
    """Verify reviewer posts loaded hash only after confirmation.

    Args:
        screen: Streamlit test application and recorded HTTP calls.
        run_view: Synthetic saved-run response used by the UI test.
        decision: Reviewer decision bound to the exact retained proposal hash.
    """
    app, calls = screen
    load_run(app, run_view)
    next(r for r in app.radio if r.label == "Reviewer decision").set_value(decision)
    next(b for b in app.button if b.label == "Submit reviewer decision").click().run()
    assert len(calls) == 1
    assert app.warning
    app.checkbox[0].check()
    next(b for b in app.button if b.label == "Submit reviewer decision").click().run()
    assert not app.exception
    assert len(calls) == 2
    assert calls[-1].url.path == f"/agent/runs/{run_view['run_id']}/approval"
    assert json.loads(calls[-1].content) == {"decision": decision, "proposal_hash": "a" * 64}


def test_credential_change_clears_loaded_proposal(screen, run_view: dict) -> None:
    """Verify credential change clears loaded proposal.

    Args:
        screen: Streamlit test application and recorded HTTP calls.
        run_view: Synthetic saved-run response used by the UI test.
    """
    app, calls = screen
    load_run(app, run_view)
    assert app.json
    app.text_input(key="agent_token").set_value("different-reviewer").run()
    assert not app.exception and not app.json
    assert len(calls) == 1
    assert not any(b.label == "Submit reviewer decision" for b in app.button)
    app.text_input(key="agent_token").set_value("").run()
    assert app.info and len(calls) == 1


def test_uncertain_action_retry_keeps_same_run_and_never_starts_new(screen, run_view: dict) -> None:
    """Verify uncertain action retry keeps same run and never starts new.

    Args:
        screen: Streamlit test application and recorded HTTP calls.
        run_view: Synthetic saved-run response used by the UI test.
    """
    app, calls = screen
    run_view["status"] = "unconfirmed"
    load_run(app, run_view)
    next(b for b in app.button if b.label == "Retry the same approved operation").click().run()
    assert not app.exception
    assert [(c.method, c.url.path) for c in calls] == [
        ("GET", f"/agent/runs/{run_view['run_id']}"),
        ("POST", f"/agent/runs/{run_view['run_id']}/retry"),
    ]


def test_invalid_customer_and_run_id_do_not_call_api(screen) -> None:
    """Verify invalid customer and run id do not call api.

    Args:
        screen: Streamlit test application and recorded HTTP calls.
    """
    app, calls = screen
    app.text_input(key="agent_customer").set_value("not-a-customer")
    next(b for b in app.button if b.label == "Prepare for approval").click().run()
    assert app.error and not calls
    app.text_input(key="agent_run_id").set_value("not-a-uuid")
    next(b for b in app.button if b.label == "Load saved run").click().run()
    assert app.error and not calls and not app.exception


@pytest.mark.parametrize("failure", ["http", "schema", "network", "storage"])
def test_api_failures_hide_stale_data_and_raw_errors(
    screen, run_view: dict, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Verify api failures hide stale data and raw errors.

    Args:
        screen: Streamlit test application and recorded HTTP calls.
        run_view: Synthetic saved-run response used by the UI test.
        monkeypatch: Pytest fixture used to isolate dependencies for this scenario.
        failure: Failure mode selected by the parametrized test.
    """
    app, calls = screen
    load_run(app, run_view)

    def fail(request: httpx.Request) -> httpx.Response:
        if failure == "network":
            raise httpx.ConnectError("raw-private-diagnostic", request=request)
        if failure == "storage":
            return httpx.Response(503, json={"detail": "Agent run storage unavailable"})
        return (
            httpx.Response(503, json={"detail": "raw-private-diagnostic"})
            if failure == "http"
            else httpx.Response(200, json={"bad": "raw-private-diagnostic"})
        )

    with httpx.Client(base_url="http://agent.test", transport=httpx.MockTransport(fail)) as client:
        monkeypatch.setattr(ui, "api_client", lambda _: client)
        next(b for b in app.button if b.label == "Load saved run").click().run()
    assert not app.exception and not app.json and app.error
    assert "raw-private-diagnostic" not in app.error[0].value
    if failure == "storage":
        assert "MongoDB/Atlas connection" in app.error[0].value
        assert "load any saved run" in app.error[0].value
    assert len(calls) == 1


def test_terminal_submitted_receipt_has_no_approval_or_retry(screen, run_view: dict) -> None:
    """Verify terminal submitted receipt has no approval or retry.

    Args:
        screen: Streamlit test application and recorded HTTP calls.
        run_view: Synthetic saved-run response used by the UI test.
    """
    app, _ = screen
    run_view["status"] = "submitted"
    response = run_view["response"]
    response["status"] = "submitted"
    response["submission"] = {
        "service_request": {
            "service_request_id": "SR-001",
            "customer_id": "NXC-0010",
            "request_type": "CALLBACK",
            "status": "RECEIVED",
            "created_at": datetime.now(UTC).isoformat(),
        },
        "evidence": response["validation"]["evidence"],
    }
    AgentRunResponse.model_validate(run_view)
    load_run(app, run_view)
    assert app.success and "not completion" in app.success[0].value
    assert not any(
        b.label in ("Submit reviewer decision", "Retry the same approved operation")
        for b in app.button
    )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, "Credential rejected"),
        (403, "customer access"),
        (404, "not accessible"),
        (409, "approval expiry"),
        (422, "request details and notes"),
        (503, "RAG and banking"),
        (500, "could not complete"),
    ],
)
def test_preparation_reports_safe_actionable_http_errors(
    screen, monkeypatch: pytest.MonkeyPatch, status: int, expected: str
) -> None:
    """Verify preparation reports safe actionable http errors.

    Args:
        screen: Streamlit test application and recorded HTTP calls.
        monkeypatch: Pytest fixture used to isolate dependencies for this scenario.
        status: HTTP or workflow status used by the scenario.
        expected: Expected outcome for the selected scenario.
    """
    app, _ = screen
    calls: list[httpx.Request] = []

    def fail(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status, json={"detail": "raw-private-diagnostic"})

    with httpx.Client(base_url="http://agent.test", transport=httpx.MockTransport(fail)) as client:
        monkeypatch.setattr(ui, "api_client", lambda _: client)
        app.text_input(key="agent_customer").set_value("NXC-0010")
        next(b for b in app.button if b.label == "Prepare for approval").click().run()
    assert not app.exception and app.error
    assert expected in app.error[0].value
    assert f"HTTP {status}" in app.error[0].value
    assert "raw-private-diagnostic" not in app.error[0].value
    assert len(calls) == 1 and calls[0].url.path == "/agent/runs"
    assert not app.json


@pytest.mark.parametrize("operation", ["approval", "retry"])
def test_failed_decision_or_retry_keeps_error_visible_and_saved_id(
    screen, run_view: dict, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """Verify failed decision or retry keeps error visible and saved id.

    Args:
        screen: Streamlit test application and recorded HTTP calls.
        run_view: Synthetic saved-run response used by the UI test.
        monkeypatch: Pytest fixture used to isolate dependencies for this scenario.
        operation: Workflow operation under test.
    """
    app, _ = screen
    if operation == "retry":
        run_view["status"] = "unconfirmed"
    load_run(app, run_view)
    if operation == "approval":
        app.checkbox[0].check()
    calls: list[httpx.Request] = []

    def fail(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(403, json={"detail": "raw-private-diagnostic"})

    with httpx.Client(base_url="http://agent.test", transport=httpx.MockTransport(fail)) as client:
        monkeypatch.setattr(ui, "api_client", lambda _: client)
        label = (
            "Submit reviewer decision"
            if operation == "approval"
            else "Retry the same approved operation"
        )
        next(b for b in app.button if b.label == label).click().run()
    assert not app.exception and app.error and not app.json
    assert "HTTP 403" in app.error[0].value
    assert "raw-private-diagnostic" not in app.error[0].value
    assert app.text_input(key="agent_run_id").value == run_view["run_id"]
    assert len(calls) == 1
    assert calls[0].url.path == f"/agent/runs/{run_view['run_id']}/{operation}"
