from __future__ import annotations

import asyncio
from datetime import date
from typing import Any, cast
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient
from langchain_core.documents import Document
from langchain_core.stores import InMemoryStore
from langchain_core.vectorstores import VectorStore
from pydantic import ValidationError

from app.api import retrieval as retrieval_api
from app.chains.retrieval import build_retrieval_chain
from app.core.config import Settings, get_settings
from app.main import create_app
from app.models.retrieval import RetrieveRequest, RetrieveResponse, RetrieveTimings
from app.services import retrieval as retrieval_service


def settings() -> Settings:
    return Settings(
        _env_file=None,
        mongodb_uri="mongodb://unused",
        mongodb_db="unused",
        mongodb_collection="unused",
        openai_api_key="unused",
        institution="NexaBank",
        jurisdiction="IN",
        confidentiality_level="internal",
    )


def test_retrieval_filters_and_expands_parent() -> None:
    document = Document(
        id="POL-HL-V2_6.2_c01",
        page_content="6.2 Processing fee",
        metadata={
            "doc_id": "POL-HL-V2",
            "title": "NexaHome Loan Policy",
            "policy_version": "2.0",
            "clause": "6.2",
            "effective_date": "2024-04-01",
            "parent_id": "POL-HL-V2_s06",
        },
    )
    store = Mock(spec=VectorStore)
    store.asimilarity_search_with_score = AsyncMock(return_value=[(document, 0.91)])
    parents = InMemoryStore()
    asyncio.run(parents.amset([("POL-HL-V2_s06", Document(page_content="Whole fee section"))]))
    request = RetrieveRequest(
        query="processing fee", as_of=date(2025, 9, 30), product_id="NEXA-HL", top_k=3
    )

    response = asyncio.run(
        build_retrieval_chain(cast(VectorStore, store), parents, settings()).ainvoke(request)
    )

    assert response.results[0].parent_text == "Whole fee section"
    assert response.results[0].citation.doc_id == "POL-HL-V2"
    assert response.results[0].rank == 1
    assert response.results[0].score == 0.91
    assert response.timings.total_ms >= response.timings.search_ms
    assert store.asimilarity_search_with_score.await_args.kwargs == {
        "k": 3,
        "pre_filter": {
            "$and": [
                {"effective_date": {"$lte": "2025-09-30"}},
                {"effective_to_search": {"$gte": "2025-09-30"}},
                {"jurisdiction": "IN"},
                {"confidentiality_level": "internal"},
                {"product_id": "NEXA-HL"},
            ]
        },
    }


def test_retrieval_empty_and_missing_parent() -> None:
    store = Mock(spec=VectorStore)
    store.asimilarity_search_with_score = AsyncMock(return_value=[])
    parents = InMemoryStore()
    request = RetrieveRequest(query="unknown", as_of=date(2026, 10, 1))
    chain = build_retrieval_chain(cast(VectorStore, store), parents, settings())
    assert asyncio.run(chain.ainvoke(request)).results == []

    document = Document(
        page_content="Cited child",
        metadata={
            "doc_id": "POL-HL-V3",
            "title": "NexaHome Loan Policy",
            "policy_version": "3.0",
            "clause": "4.1",
            "effective_date": "2025-10-01",
            "parent_id": "missing",
        },
    )
    store.asimilarity_search_with_score = AsyncMock(return_value=[(document, 0.8)])
    assert asyncio.run(chain.ainvoke(request)).results[0].parent_text == "Cited child"


def test_request_rejects_invalid_input() -> None:
    for payload in (
        {"query": " ", "as_of": "2026-10-01"},
        {"query": "fee", "as_of": "2026-10-01", "top_k": 0},
        {"query": "fee", "as_of": "2026-10-01", "extra": "unexpected"},
    ):
        try:
            RetrieveRequest.model_validate(payload)
        except ValidationError:
            continue
        raise AssertionError(f"Accepted invalid request: {payload}")


def test_api_returns_safe_failure_and_validates_body(monkeypatch: Any) -> None:
    app = create_app()
    app.dependency_overrides[get_settings] = settings
    client = TestClient(app)
    response = RetrieveResponse(
        as_of=date(2026, 10, 1),
        results=[],
        timings=RetrieveTimings(search_ms=1, parent_ms=0, total_ms=1),
    )
    monkeypatch.setattr(retrieval_api, "retrieve_policy", AsyncMock(return_value=response))
    assert client.post("/retrieve", json={"query": "fee", "as_of": "2026-10-01"}).json() == {
        "as_of": "2026-10-01",
        "results": [],
        "timings": {"search_ms": 1.0, "parent_ms": 0.0, "total_ms": 1.0},
    }
    assert client.post("/retrieve", json={"query": "", "as_of": "2026-10-01"}).status_code == 422

    monkeypatch.setattr(
        retrieval_api, "retrieve_policy", AsyncMock(side_effect=RuntimeError("secret"))
    )
    failed = client.post("/retrieve", json={"query": "fee", "as_of": "2026-10-01"})
    assert failed.status_code == 503
    assert "secret" not in failed.text


def test_health_metrics_and_failure_counters(monkeypatch: Any) -> None:
    retrieval_service.retrieval_metrics.clear()
    response = RetrieveResponse(
        as_of=date(2026, 10, 1),
        results=[],
        timings=RetrieveTimings(search_ms=1.5, parent_ms=0, total_ms=2.5),
    )
    chain = Mock()
    chain.ainvoke = AsyncMock(return_value=response)
    monkeypatch.setattr(retrieval_service, "get_embeddings", lambda _settings: object())
    monkeypatch.setattr(retrieval_service, "get_vector_store", lambda *_args: object())
    monkeypatch.setattr(retrieval_service, "get_parent_store", lambda _settings: object())
    monkeypatch.setattr(retrieval_service, "build_retrieval_chain", lambda *_args: chain)

    request = RetrieveRequest(query="unknown", as_of=date(2026, 10, 1))
    asyncio.run(retrieval_service.retrieve_policy(request, settings()))
    chain.ainvoke.side_effect = RuntimeError("Atlas unavailable")
    try:
        asyncio.run(retrieval_service.retrieve_policy(request, settings()))
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected a retrieval failure")

    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/metrics").json() == {
        "retrieval_requests_total": 2,
        "retrieval_errors_total": 1,
        "retrieval_empty_total": 1,
        "retrieval_latency_ms_total": 2.5,
    }
