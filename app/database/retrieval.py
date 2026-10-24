from __future__ import annotations

import asyncio
import re
from typing import Any

from langchain_core.documents import Document
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_mongodb.retrievers import MongoDBAtlasHybridSearchRetriever

from app.core.config import Settings
from app.database.mongo import _database


def build_amendment_search(settings: Settings) -> Runnable[dict[str, Any], list[Document]]:
    """Load complete, in-scope circulars linked to the retrieved policy IDs."""

    def load(value: dict[str, Any]) -> list[Document]:
        if not value["doc_ids"]:
            return []
        collection = _database(settings)[settings.mongodb_collection]
        pending = set(value["doc_ids"])
        visited: set[str] = set()
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        while pending:
            links: list[dict[str, Any]] = [{"doc_id": {"$in": sorted(pending)}}]
            links.extend(
                {"supersedes": {"$regex": rf"^{re.escape(identifier)}(?:\s|$)"}}
                for identifier in sorted(pending)
            )
            query = {"$and": [value["pre_filter"], {"doc_type": "circular"}, {"$or": links}]}
            for row in collection.find(query, {"embedding": 0}).sort("_id", 1):
                key = (row["doc_id"], row["policy_version"])
                if key in grouped:
                    continue
                parts = list(
                    collection.find(
                        {
                            "institution": settings.institution,
                            "doc_id": key[0],
                            "policy_version": key[1],
                        },
                        {"embedding": 0},
                    ).sort("_id", 1)
                )
                # Check the whole indexed instrument, including chunks hidden by a bad scope field.
                if not parts or any(
                    part.get(field) != row.get(field)
                    for part in parts
                    for field in (
                        "institution",
                        "jurisdiction",
                        "confidentiality_level",
                        "product_id",
                        "effective_date",
                        "effective_to",
                        "effective_to_search",
                        "doc_type",
                        "supersedes",
                        "title",
                    )
                ):
                    raise ValueError("Inconsistent amendment metadata")
                grouped[key] = parts
            visited.update(pending)
            pending = {key[0] for key in grouped} - visited
        return [
            Document(
                page_content="\n".join(dict.fromkeys(row["text"] for row in parts)),
                metadata={
                    **{key: value for key, value in parts[0].items() if key not in {"_id", "text"}},
                    "clause": None,
                },
            )
            for parts in grouped.values()
        ]

    async def search(value: dict[str, Any]) -> list[Document]:
        return await asyncio.to_thread(load, value)

    return RunnableLambda(search).with_config(run_name="linked_policy_amendments")


def build_hybrid_search(
    vector_store: MongoDBAtlasVectorSearch, settings: Settings
) -> Runnable[dict[str, Any], list[tuple[Document, float]]]:
    """Atlas BM25 + vector search fused by RRF, with no automatic index creation."""

    async def search(value: dict[str, Any]) -> list[tuple[Document, float]]:
        retriever = MongoDBAtlasHybridSearchRetriever(
            vectorstore=vector_store,
            search_index_name=settings.text_index_name,
            k=value["k"],
            pre_filter=value["pre_filter"],
            auto_create_index=False,
        )
        documents = await retriever.ainvoke(value["query"])
        return [(document, float(document.metadata["score"])) for document in documents]

    return RunnableLambda(search).with_config(run_name="atlas_hybrid_rrf")


def resolve_reference_contexts(settings: Settings, references: list[dict[str, Any]]) -> list[str]:
    """Resolve golden source references to actual indexed text, in reference order."""
    collection = _database(settings)[settings.mongodb_collection]
    texts = []
    for reference in references:
        query = {
            "doc_id": reference["doc_id"],
            "institution": settings.institution,
            "jurisdiction": settings.jurisdiction,
            "confidentiality_level": settings.confidentiality_level,
        }
        if reference.get("clause") is not None:
            query["clause"] = reference["clause"]
        documents = list(collection.find(query, {"text": 1}).sort("_id", 1))
        if not documents:
            raise ValueError(f"Golden reference is not indexed: {reference['doc_id']}")
        texts.append("\n".join(document["text"] for document in documents))
    return texts
