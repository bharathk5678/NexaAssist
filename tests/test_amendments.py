from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock

import mongomock
import pytest
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda
from langchain_core.stores import InMemoryStore

from app.chains.retrieval import build_retrieval_chain
from app.core.config import Settings
from app.database import retrieval as database
from app.models.retrieval import RetrieveRequest


@pytest.mark.parametrize("as_of,expected", [("2026-06-30", 0), ("2026-07-01", 1)])
def test_linked_circular_keeps_fee_and_applicability_in_scope(
    monkeypatch: pytest.MonkeyPatch, settings: Settings, as_of: str, expected: int
) -> None:
    storage: Any = mongomock.MongoClient().db
    settings = settings.model_copy(update={"mongodb_collection": "chunks"})
    monkeypatch.setattr(database, "_database", lambda _: storage)
    metadata = {
        "doc_id": "CIR-2026-07",
        "policy_version": "1.0",
        "title": "Fee circular",
        "institution": "NexaBank",
        "product_id": "NEXA-HL",
        "jurisdiction": "IN",
        "confidentiality_level": "internal",
        "doc_type": "circular",
        "effective_date": "2026-07-01",
        "effective_to_search": "9999-12-31",
        "supersedes": "POL-HL-V3 (clauses 6.2, 8.3 only)",
    }
    texts = [
        "Fee 0.30%, minimum 5,000, maximum 10,000 plus GST.",
        "Applies to sanctions on or after 2026-07-01; earlier sanctions keep their fee.",
    ]
    for i, text in enumerate(texts):
        storage.chunks.insert_one({**metadata, "_id": f"CIR-{i}", "text": text})
    storage.chunks.insert_many(
        [
            {**metadata, "_id": "foreign", "institution": "OtherBank", "text": "Foreign secret"},
            {
                **metadata,
                "_id": "unrelated",
                "doc_id": "CIR-UNRELATED",
                "supersedes": "POL-HL-V30",
                "text": "Unrelated fee",
            },
            {
                **metadata,
                "_id": "expired",
                "doc_id": "CIR-EXPIRED",
                "effective_to_search": "2026-06-29",
                "text": "Expired",
            },
        ]
    )
    document = Document(
        page_content="Base fee 0.35%",
        metadata={
            **metadata,
            "doc_id": "POL-HL-V3",
            "doc_type": "policy",
            "clause": "6.2",
            "parent_id": "missing",
        },
    )
    vector = Mock()
    vector.asimilarity_search_with_score = AsyncMock(return_value=[(document, 0.9)])
    result = asyncio.run(
        build_retrieval_chain(
            vector,
            InMemoryStore(),
            settings,
            amendment_search=database.build_amendment_search(settings),
        ).ainvoke(RetrieveRequest(query="fee", as_of=as_of, top_k=1, product_id="NEXA-HL"))
    )
    assert len(result.results) == 1
    assert len(result.amendments) == expected
    if expected:
        context = result.amendments[0].parent_text
        assert all(text in context for text in texts)
        assert not any(text in context for text in ("Foreign secret", "Unrelated fee", "Expired"))
        assert result.evidence[0].citation.doc_id == "CIR-2026-07"


@pytest.mark.parametrize("hybrid", [False, True])
def test_dense_and_hybrid_use_the_same_institution_scope(settings: Settings, hybrid: bool) -> None:
    vector = Mock()
    vector.asimilarity_search_with_score = AsyncMock(return_value=[])
    search = AsyncMock(return_value=[])
    asyncio.run(
        build_retrieval_chain(
            vector,
            InMemoryStore(),
            settings,
            candidate_search=RunnableLambda(search) if hybrid else None,
        ).ainvoke(RetrieveRequest(query="fee", as_of="2026-10-01"))
    )
    filters = (
        search.await_args.args[0]["pre_filter"]
        if hybrid
        else vector.asimilarity_search_with_score.await_args.kwargs["pre_filter"]
    )
    assert {"institution": settings.institution} in filters["$and"]


def test_amendments_follow_links_until_no_new_instrument_remains(
    monkeypatch: pytest.MonkeyPatch, settings: Settings
) -> None:
    storage: Any = mongomock.MongoClient().db
    monkeypatch.setattr(database, "_database", lambda _: storage)
    for name, supersedes in (("A", "P"), ("B", "A"), ("C", "B")):
        storage[settings.mongodb_collection].insert_one(
            {
                "doc_id": name,
                "policy_version": "1",
                "institution": settings.institution,
                "doc_type": "circular",
                "supersedes": supersedes,
                "text": name,
            }
        )
    result = asyncio.run(
        database.build_amendment_search(settings).ainvoke(
            {"doc_ids": ["P"], "pre_filter": {"institution": settings.institution}}
        )
    )
    assert {x.metadata["doc_id"] for x in result} == {"A", "B", "C"}


@pytest.mark.parametrize(
    "changed_field,changed_value",
    [
        ("effective_to_search", "2025-01-01"),
        ("effective_to_search", None),
        ("product_id", "NEXA-PL"),
    ],
)
def test_inconsistent_circular_fails_closed_instead_of_returning_a_partial_instrument(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
    changed_field: str,
    changed_value: str | None,
) -> None:
    storage: Any = mongomock.MongoClient().db
    monkeypatch.setattr(database, "_database", lambda _: storage)
    metadata = {
        "institution": settings.institution,
        "doc_id": "CIR-A",
        "policy_version": "1",
        "doc_type": "circular",
        "product_id": "NEXA-HL",
        "supersedes": "P",
        "effective_to_search": "9999-12-31",
    }
    storage[settings.mongodb_collection].insert_many(
        [
            {**metadata, "text": "Fee changed"},
            {**metadata, changed_field: changed_value, "text": "Sanction-date condition"},
        ]
    )
    with pytest.raises(ValueError, match="Inconsistent amendment metadata"):
        asyncio.run(
            database.build_amendment_search(settings).ainvoke(
                {
                    "doc_ids": ["P"],
                    "pre_filter": {
                        "institution": settings.institution,
                        "effective_to_search": {"$gte": "2026-10-01"},
                    },
                }
            )
        )
