from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from app.agents.orchestrator import build_agent_graph
from app.models.agent import AgentRequest, IntentDecision
from app.models.retrieval import RetrieveResponse
from app.models.validation import (
    ServiceRequestProposal,
    SubmittedServiceRequest,
    ValidationAccess,
    ValidationEvidence,
    ValidationResult,
)

TYPES = [
    "STATEMENT_COPY",
    "CALLBACK",
    "RE_KYC_REMINDER",
    "INTEREST_CERTIFICATE",
    "OPT_IN_CIR_2026_07_PART_PREPAY",
]


@pytest.mark.parametrize("request_type", TYPES)
@pytest.mark.parametrize("failure", [None, "wrong_approval", "tampered_checkpoint"])
@pytest.mark.parametrize("classified_intent", ["supported_action", "customer_context"])
def test_four_agent_path_pauses_then_executes_once(
    request_type: str, failure: str | None, classified_intent: str
) -> None:
    request = AgentRequest.model_validate(
        {
            "query": "Prepare the requested service.",
            "as_of": "2026-10-01",
            "customer_id": "NXC-0010",
            "product_id": "NEXA-HL",
            "action": "createServiceRequest",
            "action_details": {"request_type": request_type, "loan_account_id": "NXL-HL-0010"},
        }
    )
    evidence = RetrieveResponse.model_validate(
        {
            "as_of": "2026-10-01",
            "results": [],
            "amendments": [],
            "timings": {"search_ms": 1, "parent_ms": 1, "total_ms": 2},
        }
    )
    assert request.action_details is not None
    validation = ValidationResult(
        decision="allowed",
        reason="Published permission and ownership checked.",
        proposal=ServiceRequestProposal.model_validate(
            {
                "customer_id": "NXC-0010",
                **request.action_details.model_dump(),
            }
        ),
        evidence=[
            ValidationEvidence.model_validate(
                {
                    "quote": "An exact retained source quote.",
                    "citation": {
                        "doc_id": "POL-TEST",
                        "title": "Policy",
                        "policy_version": "1.0",
                        "clause": "5.1",
                        "effective_date": "2025-01-01",
                    },
                }
            )
        ],
    )
    choice = IntentDecision.model_validate(
        {
            "intent": classified_intent,
            "product_id": None,
            "as_of": None,
            "customer_id": None,
            "action": None,
            "product_required": False,
            "missing_fields": [],
        }
    )
    retrieve, validate, answer = (
        AsyncMock(return_value=evidence),
        AsyncMock(return_value=validation),
        AsyncMock(),
    )
    submit = AsyncMock(
        return_value=SubmittedServiceRequest.model_validate(
            {
                "service_request": {
                    "service_request_id": "NXSR-000001",
                    "customer_id": "NXC-0010",
                    "request_type": request_type,
                    "loan_account_id": "NXL-HL-0010",
                    "status": "RECEIVED",
                    "created_at": "2026-10-27T00:00:00Z",
                },
                "evidence": [item.model_dump(mode="json") for item in validation.evidence],
            }
        )
    )
    saver = InMemorySaver()

    def graph():
        return build_agent_graph(
            RunnableLambda(lambda _: choice),
            RunnableLambda(retrieve),
            answer,
            validator=validate,
            access=ValidationAccess(customer_ids={"NXC-0010"}),
            actioner=submit,
            checkpointer=saver,
        )

    async def run() -> None:
        config = {"configurable": {"thread_id": "test-run"}, "recursion_limit": 12}
        first = graph()
        state = await first.ainvoke(
            {"request": request, "idempotency_key": "stable-training-key"}, config
        )
        assert state["__interrupt__"]
        submit.assert_not_awaited()
        retrieve.assert_awaited_once()
        checkpoint = await first.aget_state(config)
        assert checkpoint.next == ("approval",)
        if failure == "wrong_approval":
            with pytest.raises(ValueError, match="does not match"):
                await graph().ainvoke(
                    Command(resume={"decision": "approve", "proposal_hash": "0" * 64}), config
                )
            submit.assert_not_awaited()
            return
        if failure == "tampered_checkpoint":
            await graph().aupdate_state(config, {"approved_hash": "0" * 64}, as_node="revalidate")
            with pytest.raises(ValueError, match="exact approved proposal"):
                await graph().ainvoke(None, config)
            submit.assert_not_awaited()
            return
        resumed = await graph().ainvoke(
            Command(
                resume={
                    "decision": "approve",
                    "proposal_hash": checkpoint.values["proposal_hash"],
                }
            ),
            config,
        )
        assert resumed["response"].status == "submitted"
        assert resumed["response"].submission.service_request.service_request_id == "NXSR-000001"
        assert retrieve.await_count == 2  # One per start/resume HTTP request.
        assert validate.await_count == 2
        submit.assert_awaited_once_with(request, validation, "stable-training-key")
        await graph().ainvoke(None, config)
        submit.assert_awaited_once()
        answer.assert_not_awaited()

    asyncio.run(run())


@pytest.mark.parametrize("validator", [None, AsyncMock()])
def test_action_cannot_be_configured_without_validation_and_checkpointing(validator) -> None:
    with pytest.raises(ValueError, match="checkpointing"):
        build_agent_graph(
            Mock(spec=Runnable),
            Mock(spec=Runnable),
            AsyncMock(),
            validator=validator,
            actioner=AsyncMock(),
            checkpointer=InMemorySaver() if validator is None else None,
        )
