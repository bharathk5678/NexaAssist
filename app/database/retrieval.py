from __future__ import annotations

from typing import Any

from langchain_core.documents import Document
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_mongodb.retrievers import MongoDBAtlasHybridSearchRetriever

from app.core.config import Settings
from app.database.mongo import _database


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
