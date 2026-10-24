from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import Mock

import httpx
import mongomock
import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.runnables import RunnableLambda
from langchain_core.stores import InMemoryStore
from langchain_mongodb import MongoDBAtlasVectorSearch

from app.chains.rerank import build_rerank_chain, completion_probabilities, relevance_probability
from app.core.config import Settings
from app.database.retrieval import build_hybrid_search
from app.models.retrieval import RetrieveRequest
from app.services import retrieval as retrieval_service


@pytest.mark.parametrize("hybrid", [False, True])
@pytest.mark.parametrize("rerank", [False, True])
def test_service_applies_configured_search_and_reranking(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, hybrid: bool, rerank: bool
) -> None:
    from unittest.mock import AsyncMock

    settings = settings.model_copy(
        update={"retrieval_mode": "hybrid" if hybrid else "dense", "rerank_enabled": rerank}
    )
    rows = [
        (
            Document(
                page_content=f"Policy passage {number}",
                metadata={
                    "doc_id": f"POL-{number}",
                    "title": "Policy",
                    "policy_version": "1",
                    "clause": "4.1",
                    "effective_date": "2026-01-01",
                    "parent_id": f"parent-{number}",
                },
            ),
            score,
        )
        for number, score in ((1, 0.9), (2, 0.8))
    ]
    vector = Mock()
    vector.asimilarity_search_with_score = AsyncMock(return_value=rows)
    hybrid_search = AsyncMock(return_value=rows)
    reranker = AsyncMock(return_value=list(reversed(rows)))
    hybrid_factory = Mock(return_value=RunnableLambda(hybrid_search))
    rerank_factory = Mock(return_value=RunnableLambda(reranker))
    monkeypatch.setattr(retrieval_service, "get_embeddings", lambda _: object())
    monkeypatch.setattr(retrieval_service, "get_vector_store", lambda *_: vector)
    monkeypatch.setattr(retrieval_service, "get_parent_store", lambda _: InMemoryStore())
    monkeypatch.setattr(
        retrieval_service, "build_amendment_search", lambda _: RunnableLambda(lambda _: [])
    )
    monkeypatch.setattr(retrieval_service, "build_hybrid_search", hybrid_factory, raising=False)
    monkeypatch.setattr(retrieval_service, "build_rerank_chain", rerank_factory, raising=False)
    response = asyncio.run(
        retrieval_service.retrieve_policy(
            RetrieveRequest(query="loan limit", as_of="2026-10-01", top_k=1), settings
        )
    )
    assert response.results[0].citation.doc_id == ("POL-2" if rerank else "POL-1")
    assert hybrid_factory.call_count == int(hybrid)
    assert rerank_factory.call_count == int(rerank)
    assert hybrid_search.await_count == int(hybrid)
    assert vector.asimilarity_search_with_score.await_count == int(not hybrid)
    expected_k = settings.retrieval_candidates if rerank else 1
    if hybrid:
        assert hybrid_search.await_args is not None
        assert hybrid_search.await_args.args[0]["k"] == expected_k
    else:
        assert vector.asimilarity_search_with_score.await_args.kwargs["k"] == expected_k
    if rerank:
        assert reranker.await_args is not None
        assert reranker.await_args.args[0]["rows"] == rows
    assert len(response.results) == 1


def test_hybrid_pipeline_filters_both_branches_before_ranking(settings: Settings) -> None:
    collection: Any = mongomock.MongoClient().db.chunks
    collection.aggregate = Mock(
        return_value=[
            {
                "_id": "POL-1_4.1_c01",
                "text": "loan limit",
                "score": 0.03,
                "parent_id": "POL-1_s04",
            }
        ]
    )
    store = MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=DeterministicFakeEmbedding(size=8),
        index_name="vector",
        auto_create_index=False,
    )
    filters = {"$and": [{"product_id": "HOME"}, {"effective_date": {"$lte": "2026-10-01"}}]}
    rows = asyncio.run(
        build_hybrid_search(store, settings).ainvoke(
            {
                "query": "POL-1 loan limit",
                "k": 20,
                "pre_filter": filters,
            }
        )
    )
    assert rows[0][0].page_content == "loan limit"
    assert rows[0][1] == 0.03
    pipeline = collection.aggregate.call_args.args[0]
    branches = [stage["$unionWith"]["pipeline"] for stage in pipeline if "$unionWith" in stage]
    vector = pipeline
    text = next(branch for branch in branches if "$search" in branch[0])
    assert vector[0]["$vectorSearch"]["filter"] == filters
    assert text[1] == {"$match": filters}
    assert next(i for i, s in enumerate(text) if "$match" in s) < next(
        i for i, s in enumerate(text) if "$limit" in s
    )
    assert text[0]["$search"]["index"] == settings.text_index_name


def test_ollama_content_array_logprobs() -> None:
    probabilities = completion_probabilities(
        {
            "choices": [
                {
                    "logprobs": {
                        "content": [
                            {
                                "token": "yes",
                                "logprob": -0.1,
                                "top_logprobs": [
                                    {"token": "yes", "logprob": -0.1},
                                    {"token": "no", "logprob": -9},
                                ],
                            }
                        ]
                    }
                }
            ]
        }
    )
    assert relevance_probability(probabilities) > 0.99


def test_local_reranker_uses_openai_completions_and_likelihoods(settings: Settings) -> None:
    settings = settings.model_copy(
        update={"rerank_api": "openai", "rerank_base_url": "http://127.0.0.1:11434/v1"}
    )

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/completions"
        payload = json.loads(request.content)
        assert payload["max_tokens"] == 1
        assert payload["model"] == settings.rerank_model
        useful = "right policy" in payload["prompt"]
        return httpx.Response(
            200,
            json={
                "id": "local",
                "object": "text_completion",
                "created": 1,
                "model": settings.rerank_model,
                "choices": [
                    {
                        "index": 0,
                        "text": "yes" if useful else "no",
                        "finish_reason": "length",
                        "logprobs": {
                            "top_logprobs": [
                                {"yes": -0.1 if useful else -9, "no": -9 if useful else -0.1}
                            ]
                        },
                    }
                ],
            },
        )

    rows = [
        (Document(page_content="wrong policy"), 0.9),
        (Document(page_content="right policy"), 0.5),
    ]
    ranked = asyncio.run(
        build_rerank_chain(settings, transport=httpx.MockTransport(respond)).ainvoke(
            {
                "query": "fee",
                "as_of": "2026-10-01",
                "rows": rows,
            }
        )
    )
    assert ranked[0][0].page_content == "right policy"
    assert ranked[0][1] > 0.99
    assert ranked[1][1] < 0.01


def test_native_ollama_reranker_uses_raw_scoring_prompt(settings: Settings) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/generate"
        payload = json.loads(request.content)
        assert payload["raw"] is True and payload["stream"] is False
        assert payload["options"]["num_predict"] == 1
        return httpx.Response(
            200,
            json={
                "logprobs": [
                    {
                        "top_logprobs": [
                            {"token": "yes", "logprob": -0.1},
                            {"token": "no", "logprob": -5},
                        ]
                    }
                ]
            },
        )

    ranked = asyncio.run(
        build_rerank_chain(settings, transport=httpx.MockTransport(respond)).ainvoke(
            {
                "query": "fee",
                "as_of": "2026-10-01",
                "rows": [(Document(page_content="Fee policy"), 0.9)],
            }
        )
    )
    assert ranked[0][1] > 0.99


@pytest.mark.parametrize("probabilities", [{"yes": -0.1}, {"yes": float("nan"), "no": -1}])
def test_missing_or_invalid_local_likelihoods_do_not_fabricate_scores(
    probabilities: dict[str, float],
) -> None:
    with pytest.raises(ValueError, match="yes AND no"):
        relevance_probability(probabilities)


def test_case_and_whitespace_variants_do_not_replace_qwen_scoring_tokens() -> None:
    exact = {"yes": -0.1, "no": -8}
    alternatives = {**exact, "Yes": -9, "NO": -0.01, " yes": -10, " no": -0.01}
    assert relevance_probability(alternatives) == relevance_probability(exact)


def test_case_variants_cannot_substitute_for_missing_exact_qwen_tokens() -> None:
    with pytest.raises(ValueError, match="yes AND no"):
        relevance_probability({"Yes": -0.1, "No": -8})
