from __future__ import annotations

import asyncio
import json
from contextlib import nullcontext
from datetime import date
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableLambda

from app.api import answer as answer_api
from app.chains.answer import build_answer_chain
from app.chains.context import assemble_context, render_context, token_encoder
from app.core import observability
from app.core.config import Settings, get_settings
from app.main import create_app
from app.models.retrieval import (
    Citation,
    RetrieveHit,
    RetrieveRequest,
    RetrieveResponse,
    RetrieveTimings,
)


def hit(number: int = 1, text: str = "Maximum amount is 7.5 crore.") -> RetrieveHit:
    return RetrieveHit(
        rank=number,
        score=0.9,
        text=text,
        parent_text=text,
        citation=Citation(
            doc_id=f"POL-{number}",
            title="Policy",
            policy_version="1",
            clause="4.1",
            effective_date=date(2025, 1, 1),
        ),
    )


def run_answer(settings: Settings, hits: list[RetrieveHit], draft: dict[str, Any]) -> Any:
    response = RetrieveResponse(
        as_of=date(2026, 10, 1),
        results=hits,
        timings=RetrieveTimings(search_ms=1, parent_ms=1, total_ms=2),
    )
    llm = Mock(spec=BaseChatModel)
    llm.with_structured_output.return_value = RunnableLambda(lambda _value: draft)
    chain = build_answer_chain(
        RunnableLambda(lambda _request: response), cast(BaseChatModel, llm), settings
    )
    return asyncio.run(chain.ainvoke(RetrieveRequest(query="limit", as_of=response.as_of)))


def test_answer_returns_verified_quote(settings: Settings) -> None:
    response = run_answer(
        settings,
        [hit()],
        {
            "status": "answered",
            "answer": "The maximum is 7.5 crore [1].",
            "evidence": [{"evidence_id": 1, "quote": "Maximum amount is 7.5 crore."}],
        },
    )
    assert response.status == "answered"
    assert response.citations[0].matched_child.doc_id == "POL-1"


@pytest.mark.parametrize(
    "answer,evidence",
    [
        ("7.5 crore [2]", [{"evidence_id": 1, "quote": "7.5 crore"}]),
        ("7.5 crore [2]", [{"evidence_id": 2, "quote": "7.5 crore"}]),
        ("7.5 crore [1]", [{"evidence_id": 1, "quote": "invented fee"}]),
        ("7.5 crore [1]", [{"evidence_id": 1, "quote": " "}]),
        ("7.5 crore", []),
    ],
)
def test_answer_abstains_on_invalid_citations(
    settings: Settings, answer: str, evidence: list[dict[str, Any]]
) -> None:
    response = run_answer(
        settings,
        [hit()],
        {
            "status": "answered",
            "answer": answer,
            "evidence": evidence,
        },
    )
    assert response.status == "insufficient_evidence"
    assert response.citations == []


def test_empty_retrieval_can_clarify_scope(settings: Settings) -> None:
    response = run_answer(
        settings,
        [],
        {"status": "needs_clarification", "answer": "Which product?", "evidence": []},
    )
    assert response.status == "needs_clarification"
    assert response.citations == []


@pytest.mark.parametrize("repair_succeeds", [True, False])
def test_invalid_citations_get_only_one_repair_attempt(
    settings: Settings, repair_succeeds: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    annotation = Mock(side_effect=lambda **_: nullcontext())
    monkeypatch.setattr(observability, "LLMObs", Mock(enabled=True, annotation_context=annotation))
    invalid = {
        "status": "answered",
        "answer": "The maximum is 7.5 crore [1].",
        "evidence": [{"evidence_id": 1, "quote": "invented quote"}],
    }
    valid = {
        **invalid,
        "evidence": [{"evidence_id": 1, "quote": "Maximum amount is 7.5 crore."}],
    }
    generate = Mock(side_effect=[invalid, valid if repair_succeeds else invalid])
    llm = Mock(spec=BaseChatModel)
    llm.with_structured_output.return_value = RunnableLambda(generate)
    retrieved = RetrieveResponse(
        as_of=date(2026, 10, 1),
        results=[hit()],
        timings=RetrieveTimings(search_ms=0, parent_ms=0, total_ms=0),
    )
    retrieve = Mock(return_value=retrieved)
    result = asyncio.run(
        build_answer_chain(RunnableLambda(retrieve), llm, settings).ainvoke(
            RetrieveRequest(query="maximum", as_of=retrieved.as_of)
        )
    )
    retrieve.assert_called_once()
    assert generate.call_count == 2
    assert result.status == ("answered" if repair_succeeds else "insufficient_evidence")
    assert bool(result.citations) == repair_succeeds
    prompts = [call.kwargs["prompt"] for call in annotation.call_args_list]
    assert len(prompts) == 2
    assert all(prompt["id"] == "nexaassist-policy-answer" for prompt in prompts)
    assert all(prompt["version"] == "1.0.0" for prompt in prompts)
    assert prompts[0]["variables"]["citation_feedback"] == ""
    assert "previous draft failed" in prompts[1]["variables"]["citation_feedback"]
    assert all(prompt["variables"]["query"] == "maximum" for prompt in prompts)


@pytest.mark.parametrize(
    "question",
    [
        "Which product and rate would you like to check?",
        "Should I use 31 March 2024 or the date filter?",
        "Is the fee 0.35%?",
        "NexaFlex foreclosure is four percent plus GST. Which product did you mean?",
    ],
)
def test_clarification_uses_a_fixed_scope_question_without_model_policy_claims(
    settings: Settings, question: str
) -> None:
    response = run_answer(
        settings,
        [hit()],
        {
            "status": "needs_clarification",
            "answer": question,
            "evidence": [],
        },
    )
    assert response.status == "needs_clarification"
    assert response.answer == (
        "Which product and policy date should I use, "
        "and what specific rate or policy term do you want to check?"
    )
    assert response.citations == []


def test_unfittable_amendment_abstains_before_generation(settings: Settings) -> None:
    amendment = hit(2, "applicability " * 5000)
    retrieved = RetrieveResponse(
        as_of=date(2026, 10, 1),
        results=[hit()],
        amendments=[amendment],
        timings=RetrieveTimings(search_ms=0, parent_ms=0, total_ms=0),
    )
    generate = Mock(return_value={})
    llm = Mock(spec=BaseChatModel)
    llm.with_structured_output.return_value = RunnableLambda(generate)
    result = asyncio.run(
        build_answer_chain(
            RunnableLambda(lambda _: retrieved),
            llm,
            settings.model_copy(update={"context_max_tokens": 256}),
        ).ainvoke(RetrieveRequest(query="fee", as_of=retrieved.as_of))
    )
    assert result.status == "insufficient_evidence"
    generate.assert_not_called()


def test_context_budget_deduplicates_and_preserves_whole_passages() -> None:
    first = hit().model_copy(update={"parent_text": "large parent " * 2000})
    sources = assemble_context([first, first, hit(2), hit(3), hit(4)], 256, "o200k_base")
    payload = render_context(sources)
    assert len(token_encoder("o200k_base").encode(payload)) <= 256
    assert len({item.citation.doc_id for item in sources.values()}) == len(sources)
    assert all(item.parent_text == item.text for item in sources.values())
    assert all(record["retrieved_context"] == hit().text for record in json.loads(payload))


def test_context_places_best_two_passages_at_edges() -> None:
    sources = assemble_context([hit(i) for i in range(1, 6)], 2000, "o200k_base")
    assert [item.rank for item in sources.values()] == [1, 3, 5, 4, 2]


def test_context_keeps_distinct_children_when_their_shared_parent_is_oversized() -> None:
    parent = "Long policy section with several clauses. " * 2000
    first = hit(text="The processing fee is 0.35 percent.").model_copy(
        update={"parent_text": parent}
    )
    second = first.model_copy(
        update={
            "rank": 2,
            "text": "This fee applies to sanctions on or after 1 July 2026.",
            "citation": first.citation.model_copy(update={"clause": "4.2"}),
        }
    )
    sources = assemble_context([first, second, first], 600, "o200k_base")
    assert [item.parent_text for item in sources.values()] == [first.text, second.text]
    assert len(token_encoder("o200k_base").encode(render_context(sources))) <= 600


def test_answer_api_validates_and_hides_provider_errors(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(answer_api, "answer_policy", AsyncMock(side_effect=TimeoutError("secret")))
    client = TestClient(app)
    response = client.post("/answer", json={"query": "fee", "as_of": "2026-10-01"})
    assert response.status_code == 503
    assert "secret" not in response.text
    assert client.post("/answer", json={"query": "", "as_of": "2026-10-01"}).status_code == 422
