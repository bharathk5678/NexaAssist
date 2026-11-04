"""Build the agent graph: classify, retrieve, validate, review and execute.

Node names, state keys and model import paths are retained for saved-run compatibility."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypedDict

from langchain_core.runnables import Runnable
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from app.agents.guardrails import unsafe_input
from app.models.agent import AgentRequest, AgentResponse, IntentDecision, MissingField
from app.models.agent_run import ApprovalDecision, proposal_digest
from app.models.answer import AnswerResponse
from app.models.retrieval import RetrieveRequest, RetrieveResponse
from app.models.validation import SubmittedServiceRequest, ValidationAccess, ValidationResult


class AgentState(TypedDict, total=False):
    """Shared graph state retained between routing, retrieval, review and execution.

    Attributes:
        decision: Reviewer decision bound to the exact retained proposal hash.
        policy_request: Resolved retrieval query and policy-date/product scope.
        retrieved: Retained policy evidence and timings carried between graph nodes.
        validation: Retained policy and banking validation for the exact proposed action.
        response: Validated answer or workflow result retained for rendering.
        idempotency_key: Persisted operation key reused for the unchanged banking submission.
        proposal_hash: Canonical fingerprint binding request, proposal and retained evidence.
        approved_hash: Fingerprint accepted by the distinct authorized reviewer.
    """

    request: AgentRequest
    decision: IntentDecision
    policy_request: RetrieveRequest
    retrieved: RetrieveResponse
    validation: ValidationResult
    response: AgentResponse
    idempotency_key: str
    proposal_hash: str
    approved_hash: str


def _validation_response(result: ValidationResult) -> AgentResponse:
    """Map initial and refreshed validation to the same public workflow response."""
    return AgentResponse(
        intent="supported_action",
        status="validated" if result.decision == "allowed" else result.decision,
        message=result.reason,
        validation=result,
    )


def build_agent_graph(
    classifier: Runnable[AgentRequest, IntentDecision],
    retriever: Runnable[RetrieveRequest, RetrieveResponse],
    answerer: Callable[[RetrieveRequest, RetrieveResponse], Awaitable[AnswerResponse]],
    *,
    validator: Callable[[AgentRequest, RetrieveResponse], Awaitable[ValidationResult]]
    | None = None,
    access: ValidationAccess | None = None,
    actioner: Callable[[AgentRequest, ValidationResult, str], Awaitable[SubmittedServiceRequest]]
    | None = None,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Reuse the policy path; optionally pause and execute an approved service request.

    Args:
        classifier: Runnable producing a structured intent decision from request scope.
        retriever: Runnable returning scoped policy evidence for the request.
        answerer: Coroutine generating a grounded answer from retained evidence.
        validator: Optional coroutine checking policy and current customer facts.
        access: Server-issued principal identity, customer entitlements and review permission.
        actioner: Optional execution callback for an exactly approved service proposal.
        checkpointer: Durable graph checkpoint store required for human-reviewed actions.

    Returns:
        Compiled graph preserving the durable node names and state contract.

    Raises:
        ValueError: Actions require a validator and durable workflow checkpointing.

    Example:
        graph = build_agent_graph(classifier, retriever, answerer)
    """
    if actioner is not None and (checkpointer is None or validator is None):
        raise ValueError("Actions require a validator and durable workflow checkpointing")

    async def orchestrator(state: AgentState) -> AgentState:
        """Classify a screened request and resolve missing or conflicting explicit scope."""
        request = state["request"]
        if unsafe_input(request):
            return {
                "decision": IntentDecision(
                    intent="forbidden",
                    product_id=None,
                    as_of=None,
                    customer_id=None,
                    action=None,
                    product_required=False,
                    missing_fields=[],
                )
            }
        decision = IntentDecision.model_validate(await classifier.ainvoke(request))
        if decision.intent == "forbidden":
            return {"decision": decision}
        if (
            decision.intent == "customer_context"
            and request.action == "createServiceRequest"
            and request.action_details is not None
        ):
            decision = decision.model_copy(update={"intent": "supported_action"})

        missing = list(decision.missing_fields)
        updates = {}
        scope_fields: tuple[MissingField, ...] = ("product_id", "as_of", "customer_id", "action")
        for field in scope_fields:
            explicit, extracted = getattr(request, field), getattr(decision, field)
            if explicit is not None and extracted is not None and explicit != extracted:
                missing.append(field)
            updates[field] = explicit if explicit is not None else extracted
        resolved = AgentRequest.model_validate({**request.model_dump(), **updates})
        if decision.intent == "policy_question":
            if resolved.as_of is None:
                missing.append("as_of")
            if decision.product_required and resolved.product_id is None:
                missing.append("product_id")
        if (
            decision.intent in ("customer_context", "supported_action")
            and resolved.customer_id is None
        ):
            missing.append("customer_id")
        if decision.intent == "supported_action" and resolved.action is None:
            missing.append("action")
        if (
            decision.intent == "supported_action"
            and resolved.action == "createServiceRequest"
            and validator is not None
        ):
            if resolved.as_of is None:
                missing.append("as_of")
            if resolved.action_details is None or (
                resolved.action_details.request_type
                in ("OPT_IN_CIR_2026_07_PART_PREPAY", "INTEREST_CERTIFICATE")
                and resolved.action_details.loan_account_id is None
            ):
                missing.append("action_details")
            if (
                resolved.action_details is not None
                and resolved.action_details.request_type == "OPT_IN_CIR_2026_07_PART_PREPAY"
                and resolved.product_id is None
            ):
                missing.append("product_id")
        if decision.intent == "missing_information" and not missing:
            missing.append("question")
        if missing:
            decision = decision.model_copy(
                update={
                    "intent": "missing_information",
                    "missing_fields": list(dict.fromkeys(missing)),
                }
            )
        return {"request": resolved, "decision": decision}

    async def retrieve(state: AgentState) -> AgentState:
        """Retrieve scoped policy evidence through the configured retrieval integration."""
        request = RetrieveRequest.model_validate(
            state["request"].model_dump(exclude={"customer_id", "action", "action_details"})
        )
        if state["decision"].intent == "supported_action":
            details = state["request"].action_details
            assert details is not None
            opt_in = details.request_type == "OPT_IN_CIR_2026_07_PART_PREPAY"
            request = request.model_copy(
                update={
                    "query": (
                        "CIR-2026-07 clause 5.2 existing NexaHome borrowers prepayment opt-in"
                        if opt_in
                        else "POL-OPS-001 clause 5.1 permitted advisory assistant service requests"
                    ),
                    # Operations policy is bank-wide; the selected product stays in AgentRequest.
                    "product_id": request.product_id if opt_in else None,
                }
            )
        return {"policy_request": request, "retrieved": await retriever.ainvoke(request)}

    async def grounded_answer(state: AgentState) -> AgentState:
        """Generate the policy-answer branch from evidence already retained in graph state."""
        answer = await answerer(state["policy_request"], state["retrieved"])
        return {
            "response": AgentResponse(
                intent="policy_question", status=answer.status, message=answer.answer, answer=answer
            )
        }

    def clarify(state: AgentState) -> AgentState:
        """Return a fixed request for the unresolved scope fields."""
        labels: dict[MissingField, str] = {
            "product_id": "the product",
            "as_of": "the policy lookup date (YYYY-MM-DD)",
            "customer_id": "the customer ID (NXC-0000)",
            "action": "the requested action",
            "action_details": "the required action details",
            "question": "the specific question or request",
        }
        missing = state["decision"].missing_fields
        return {
            "response": AgentResponse(
                intent="missing_information",
                status="needs_clarification",
                message="Please provide or confirm " + ", ".join(labels[f] for f in missing) + ".",
                missing_fields=missing,
            )
        }

    def forbidden(state: AgentState) -> AgentState:
        """Return the prohibited-operation response without invoking tools."""
        return {
            "response": AgentResponse(
                intent="forbidden",
                status="forbidden",
                message="I cannot carry out that request within the advisor scope. "
                "I can explain published policy and permitted service options.",
            )
        }

    def customer_context(state: AgentState) -> AgentState:
        """Report that general customer-context tools are unavailable in this stage."""
        return {
            "response": AgentResponse(
                intent="customer_context",
                status="unavailable",
                message="Customer-context tools are not connected in this stage. "
                "No customer records were accessed.",
            )
        }

    def supported_action(state: AgentState) -> AgentState:
        """Check scoped service-request capability before retrieving policy evidence."""
        request = state["request"]
        if validator is not None and request.action_details is not None:
            if (
                access is None
                or request.customer_id not in access.customer_ids
                or request.action != "createServiceRequest"
                or (
                    request.action_details.request_type == "OPT_IN_CIR_2026_07_PART_PREPAY"
                    and request.product_id != "NEXA-HL"
                )
            ):
                return {
                    "response": AgentResponse(
                        intent="supported_action",
                        status="blocked",
                        message="An authorized customer and supported service-request scope are required.",
                    )
                }
            return {}
        return {
            "response": AgentResponse(
                intent="supported_action",
                status="unavailable",
                message="This action or its required integration is unavailable. "
                "No action was performed.",
            )
        }

    async def validate(state: AgentState) -> AgentState:
        """Validate the service proposal using policy evidence and current authorized banking facts."""
        assert validator is not None
        result = await validator(state["request"], state["retrieved"])
        updates: AgentState = {"validation": result, "response": _validation_response(result)}
        if result.decision == "allowed" and actioner is not None:
            updates["proposal_hash"] = proposal_digest(state["request"], result)
        return updates

    def approval(state: AgentState) -> AgentState:
        """Pause for a decision bound to the exact proposal, then reject or retain its approved hash.

        Raises:
            ValueError: Approval does not match the pending proposal.
        """
        decision = ApprovalDecision.model_validate(
            interrupt(
                {
                    "proposal_hash": state["proposal_hash"],
                    "validation": state["validation"].model_dump(mode="json"),
                }
            )
        )
        if decision.proposal_hash != state["proposal_hash"]:
            raise ValueError("Approval does not match the pending proposal")
        if decision.decision == "reject":
            return {
                "response": AgentResponse(
                    intent="supported_action",
                    status="rejected",
                    message="The proposal was rejected. No action was performed.",
                    validation=state["validation"],
                )
            }
        return {"approved_hash": decision.proposal_hash}

    async def revalidate(state: AgentState) -> AgentState:
        """Refresh policy and banking facts and block a proposal that changed after approval."""
        assert validator is not None
        evidence = await retriever.ainvoke(state["policy_request"])
        result = await validator(state["request"], evidence)
        if (
            result.decision == "allowed"
            and proposal_digest(state["request"], result) != state["approved_hash"]
        ):
            result = ValidationResult(
                decision="blocked",
                evidence=result.evidence,
                reason="The proposal or policy evidence changed. Start a new run for fresh approval.",
            )
        return {
            "retrieved": evidence,
            "validation": result,
            "response": _validation_response(result),
        }

    async def action(state: AgentState) -> AgentState:
        """Execute only the currently authorized proposal matching the retained approval hash.

        Raises:
            ValueError: Execution requires authorization and an exact approved proposal.
        """
        if (
            actioner is None
            or access is None
            or state["request"].customer_id not in access.customer_ids
            or state.get("approved_hash") != proposal_digest(state["request"], state["validation"])
        ):
            raise ValueError("Execution requires authorization and an exact approved proposal")
        result = await actioner(state["request"], state["validation"], state["idempotency_key"])
        return {
            "response": AgentResponse(
                intent="supported_action",
                status="submitted",
                message="The bank accepted the service request. It has not necessarily completed it.",
                validation=state["validation"],
                submission=result,
            )
        }

    graph = StateGraph(AgentState)
    graph.add_node("orchestrator", orchestrator)
    graph.add_node("retriever", retrieve)
    graph.add_node("grounded_answer", grounded_answer)
    graph.add_node("clarification", clarify)
    graph.add_node("forbidden", forbidden)
    graph.add_node("customer_context", customer_context)
    graph.add_node("supported_action", supported_action)
    graph.add_node("validator", validate)
    graph.add_node("approval", approval)
    graph.add_node("revalidate", revalidate)
    graph.add_node("action", action)
    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        lambda state: state["decision"].intent,
        {
            "policy_question": "retriever",
            "missing_information": "clarification",
            "forbidden": "forbidden",
            "customer_context": "customer_context",
            "supported_action": "supported_action",
        },
    )
    graph.add_conditional_edges(
        "supported_action",
        lambda state: "end" if "response" in state else "retrieve",
        {"end": END, "retrieve": "retriever"},
    )
    graph.add_conditional_edges(
        "retriever",
        lambda state: (
            "validator" if state["decision"].intent == "supported_action" else "grounded_answer"
        ),
        {"validator": "validator", "grounded_answer": "grounded_answer"},
    )
    for node in (
        "grounded_answer",
        "clarification",
        "forbidden",
        "customer_context",
    ):
        graph.add_edge(node, END)
    graph.add_conditional_edges(
        "validator",
        lambda state: (
            "approval"
            if actioner is not None and state["validation"].decision == "allowed"
            else "end"
        ),
        {"approval": "approval", "end": END},
    )
    graph.add_conditional_edges(
        "approval",
        lambda state: "revalidate" if "approved_hash" in state else "end",
        {"revalidate": "revalidate", "end": END},
    )
    graph.add_conditional_edges(
        "revalidate",
        lambda state: "action" if state["validation"].decision == "allowed" else "end",
        {"action": "action", "end": END},
    )
    graph.add_edge("action", END)
    return graph.compile(checkpointer=checkpointer)
