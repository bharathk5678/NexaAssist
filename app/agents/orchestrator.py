from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypedDict

from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.models.agent import AgentRequest, AgentResponse, IntentDecision, MissingField
from app.models.answer import AnswerResponse
from app.models.retrieval import RetrieveRequest, RetrieveResponse


class AgentState(TypedDict, total=False):
    request: AgentRequest
    decision: IntentDecision
    policy_request: RetrieveRequest
    retrieved: RetrieveResponse
    response: AgentResponse


def build_agent_graph(
    classifier: Runnable[AgentRequest, IntentDecision],
    retriever: Runnable[RetrieveRequest, RetrieveResponse],
    answerer: Callable[[RetrieveRequest, RetrieveResponse], Awaitable[AnswerResponse]],
) -> CompiledStateGraph:
    """One bounded graph for the current Orchestrator/Retriever stage."""

    async def orchestrator(state: AgentState) -> AgentState:
        request = state["request"]
        decision = IntentDecision.model_validate(await classifier.ainvoke(request))
        if decision.intent == "forbidden":
            return {"decision": decision}

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
        request = RetrieveRequest.model_validate(
            state["request"].model_dump(exclude={"customer_id", "action"})
        )
        return {"policy_request": request, "retrieved": await retriever.ainvoke(request)}

    async def grounded_answer(state: AgentState) -> AgentState:
        answer = await answerer(state["policy_request"], state["retrieved"])
        return {
            "response": AgentResponse(
                intent="policy_question", status=answer.status, message=answer.answer, answer=answer
            )
        }

    def clarify(state: AgentState) -> AgentState:
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
        return {
            "response": AgentResponse(
                intent="forbidden",
                status="forbidden",
                message="I cannot carry out that request within the advisor scope. "
                "I can explain published policy and permitted service options.",
            )
        }

    def customer_context(state: AgentState) -> AgentState:
        return {
            "response": AgentResponse(
                intent="customer_context",
                status="unavailable",
                message="Customer-context tools are not connected in this stage. "
                "No customer records were accessed.",
            )
        }

    def supported_action(state: AgentState) -> AgentState:
        return {
            "response": AgentResponse(
                intent="supported_action",
                status="unavailable",
                message="This action requires the Validator and Action stages, "
                "which are not connected yet. No action was performed.",
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
    graph.add_edge("retriever", "grounded_answer")
    for node in (
        "grounded_answer",
        "clarification",
        "forbidden",
        "customer_context",
        "supported_action",
    ):
        graph.add_edge(node, END)
    return graph.compile()
