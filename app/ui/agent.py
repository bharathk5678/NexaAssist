"""Prepare, load, review and recover saved service-request runs in Streamlit."""

from __future__ import annotations

from datetime import date
from typing import get_args
from uuid import UUID

import httpx
import streamlit as st
from pydantic import ValidationError

from app.models.agent import AgentRequest
from app.models.agent_run import AgentRunResponse
from app.models.validation import ServiceRequestDetails, ServiceRequestType


def clear_run() -> None:
    """Discard the loaded proposal and prior error when the active credential or run changes."""
    st.session_state.pop("agent_run", None)
    st.session_state.pop("agent_run_error", None)


def request_run(
    client: httpx.Client, method: str, path: str, token: str, body: dict | None = None
) -> AgentRunResponse | None:
    """Call a durable-run endpoint and retain either a validated result or a safe UI error.

    Args:
        client: HTTP client configured for the required upstream service.
        method: Method supplied by the caller.
        path: Input file or resource path for this operation.
        token: Token supplied by the caller.
        body: Request payload used by this mock operation or test.

    Returns:
        Validated run view, or None after retaining a safe request error.
    """
    clear_run()
    try:
        response = client.request(
            method, path, headers={"Authorization": "Bearer " + token}, json=body
        )
        if response.status_code == 503 and response.json() == {
            "detail": "Agent run storage unavailable"
        }:
            st.session_state["agent_run_error"] = (
                "Agent run storage is unavailable. Check the Agent API's MongoDB/Atlas connection, "
                "then load any saved run before retrying."
            )
            return None
        response.raise_for_status()
        result = AgentRunResponse.model_validate(response.json())
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        message = {
            401: "Credential rejected. Enter a configured named agent credential.",
            403: "Access denied. Check your named agent credential and its customer access. "
            "Approval requires a different authorized reviewer.",
            404: "Saved run not found or not accessible with this credential. Check the run ID "
            "and use its owner or an authorized reviewer credential.",
            409: "This run cannot perform that operation in its current state. Load the saved "
            "run and check its status and approval expiry before continuing.",
            422: "The request was rejected. Check the customer ID, request details and notes; "
            "remove sensitive identifiers or instruction overrides.",
            503: "The Agent API could not complete the operation. Check the RAG and banking "
            "services and Agent API logs. Load any saved run before retrying.",
        }.get(
            status,
            "The Agent API could not complete the operation. Load any saved run before retrying.",
        )
        st.session_state["agent_run_error"] = f"{message} (HTTP {status})"
        return None
    except httpx.HTTPError:
        st.session_state["agent_run_error"] = (
            "The Agent API connection failed or timed out. Check that the service is running. "
            "Load any saved run before retrying; for an uncertain submission, retry that same run."
        )
        return None
    except ValueError:
        st.session_state["agent_run_error"] = (
            "The Agent API returned an invalid response. Load any saved run before retrying."
        )
        return None
    st.session_state["agent_run"] = result
    return result


def agent_workspace(client: httpx.Client, as_of: date, product_id: str | None) -> None:
    """Render the owner-to-reviewer service-request workflow and safe saved-run recovery.

    Args:
        client: HTTP client configured for the required upstream service.
        as_of: As of supplied by the caller.
        product_id: Product id identifying the scoped record.

    Example:
        agent_workspace(client, policy_date, selected_product)
    """
    st.title("Service requests", anchor=False)
    st.caption("A different authorized reviewer must approve each proposal before submission.")
    token = st.text_input(
        "Agent credential", type="password", key="agent_token", on_change=clear_run
    )
    if not token:
        clear_run()
        st.info("Enter your owner or reviewer credential. Customer access is checked by the API.")
        return

    with st.expander("Start a request"):
        with st.form("agent_start"):
            customer = st.text_input("Customer ID", key="agent_customer")
            kind = st.selectbox(
                "Request type", get_args(ServiceRequestType.__value__), key="agent_kind"
            )
            loan = st.text_input("Loan account ID (required for opt-in and certificate)")
            notes = st.text_area("Request notes (optional)", max_chars=500)
            st.caption(f"Policy scope: {as_of.isoformat()} · {product_id or 'all products'}")
            start = st.form_submit_button("Prepare for approval")
        if start:
            try:
                request = AgentRequest(
                    query=f"Create a {kind} service request for the selected customer.",
                    customer_id=customer,
                    as_of=as_of,
                    product_id=product_id,
                    action="createServiceRequest",
                    action_details=ServiceRequestDetails(
                        request_type=kind,
                        loan_account_id=loan.strip() or None,
                        notes=notes.strip() or None,
                    ),
                )
            except ValidationError:
                st.error("Check the customer ID and request details.")
            else:
                result = request_run(
                    client, "POST", "/agent/runs", token, request.model_dump(mode="json")
                )
                if result is not None:
                    st.session_state["agent_run_id"] = str(result.run_id)

    run_id = st.text_input("Saved run ID", key="agent_run_id", on_change=clear_run)
    if st.button("Load saved run"):
        try:
            identifier = UUID(run_id)
        except ValueError:
            clear_run()
            st.error("Enter a valid saved run ID.")
        else:
            request_run(client, "GET", f"/agent/runs/{identifier}", token)

    if error := st.session_state.get("agent_run_error"):
        st.error(error)
    result = st.session_state.get("agent_run")
    if result is None:
        return
    st.write(f"Status: {result.status}")
    st.code(str(result.run_id), language=None)
    st.caption(f"Approval expires: {result.expires_at.isoformat()}")
    if result.response is not None:
        st.write(result.response.message)
        if result.response.validation is not None:
            with st.expander("Proposal and policy evidence", expanded=True):
                st.json(result.response.validation.model_dump(mode="json"))
        if result.response.submission is not None:
            st.success("The bank received this request. Receipt acceptance is not completion.")
            st.json(result.response.submission.model_dump(mode="json"))

    if result.status == "pending_approval" and result.proposal_hash is not None:
        st.caption(f"Proposal fingerprint: {result.proposal_hash}")
        with st.form("agent_approval"):
            decision = st.radio("Reviewer decision", ["reject", "approve"], horizontal=True)
            confirmed = st.checkbox("I reviewed this exact proposal and its policy evidence.")
            submit = st.form_submit_button("Submit reviewer decision")
        if submit:
            if not confirmed:
                st.warning("Review the proposal and confirm before submitting a decision.")
            else:
                request_run(
                    client,
                    "POST",
                    f"/agent/runs/{result.run_id}/approval",
                    token,
                    {"decision": decision, "proposal_hash": result.proposal_hash},
                )
                st.rerun()
    elif result.status == "unconfirmed":
        st.warning("The bank may already have received this operation. Keep this saved run.")
        if st.button("Retry the same approved operation"):
            request_run(client, "POST", f"/agent/runs/{result.run_id}/retry", token)
            st.rerun()
