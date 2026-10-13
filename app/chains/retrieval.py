from __future__ import annotations

from time import perf_counter

import structlog
from langchain_core.documents import Document
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.stores import BaseStore
from langchain_core.vectorstores import VectorStore

from app.core.config import Settings
from app.models.retrieval import (
    Citation,
    RetrieveHit,
    RetrieveRequest,
    RetrieveResponse,
    RetrieveTimings,
)

logger = structlog.get_logger()


def build_retrieval_chain(
    vector_store: VectorStore,
    parent_store: BaseStore[str, Document],
    settings: Settings,
) -> Runnable[RetrieveRequest, RetrieveResponse]:
    """Search indexed policy chunks, then expand each hit to its parent section."""

    async def retrieve(request: RetrieveRequest) -> RetrieveResponse:
        as_of = request.as_of.isoformat()
        filters: list[dict[str, object]] = [
            {"effective_date": {"$lte": as_of}},
            {"effective_to_search": {"$gte": as_of}},
            {"jurisdiction": request.jurisdiction or settings.jurisdiction},
            {"confidentiality_level": settings.confidentiality_level},
        ]
        if request.product_id is not None:
            filters.append({"product_id": request.product_id})

        started = perf_counter()
        rows = await vector_store.asimilarity_search_with_score(
            request.query, k=request.top_k, pre_filter={"$and": filters}
        )
        searched = perf_counter()
        parent_ids = [document.metadata["parent_id"] for document, _ in rows]
        parents = await parent_store.amget(parent_ids) if parent_ids else []
        expanded = perf_counter()

        hits = []
        for rank, ((document, score), parent) in enumerate(zip(rows, parents, strict=True), 1):
            if parent is None:
                logger.warning("parent_section_missing", parent_id=document.metadata["parent_id"])
            hits.append(
                RetrieveHit(
                    rank=rank,
                    score=score,
                    text=document.page_content,
                    parent_text=parent.page_content if parent else document.page_content,
                    citation=Citation.model_validate(
                        {
                            key: document.metadata[key]
                            for key in (
                                "doc_id",
                                "title",
                                "policy_version",
                                "clause",
                                "effective_date",
                            )
                        }
                    ),
                )
            )

        return RetrieveResponse(
            as_of=request.as_of,
            results=hits,
            timings=RetrieveTimings(
                search_ms=round((searched - started) * 1000, 2),
                parent_ms=round((expanded - searched) * 1000, 2),
                total_ms=round((perf_counter() - started) * 1000, 2),
            ),
        )

    return RunnableLambda(retrieve).with_config(run_name="retrieve_policy")
