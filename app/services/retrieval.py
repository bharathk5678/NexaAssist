from __future__ import annotations

from collections import Counter

import structlog

from app.chains.embeddings import get_embeddings
from app.chains.rerank import build_rerank_chain
from app.chains.retrieval import build_retrieval_chain
from app.core.config import Settings
from app.core.observability import retrieval_latencies
from app.database.mongo import get_parent_store, get_vector_store
from app.database.retrieval import build_hybrid_search
from app.models.retrieval import RetrieveRequest, RetrieveResponse

logger = structlog.get_logger()
retrieval_metrics: Counter[str] = Counter()


async def retrieve_policy(request: RetrieveRequest, settings: Settings) -> RetrieveResponse:
    retrieval_metrics["requests"] += 1
    try:
        vector_store = get_vector_store(settings, get_embeddings(settings))
        chain = build_retrieval_chain(
            vector_store,
            get_parent_store(settings),
            settings,
            candidate_search=build_hybrid_search(vector_store, settings)
            if settings.retrieval_mode == "hybrid"
            else None,
            reranker=build_rerank_chain(settings) if settings.rerank_enabled else None,
        )
        response = await chain.ainvoke(request)
    except Exception:
        retrieval_metrics["errors"] += 1
        raise
    if not response.results:
        retrieval_metrics["empty"] += 1
        logger.warning("retrieval_empty", as_of=request.as_of.isoformat())
    retrieval_metrics["latency_us_total"] += round(response.timings.total_ms * 1000)
    retrieval_latencies.append(response.timings.total_ms)
    logger.info(
        "retrieval_completed",
        result_count=len(response.results),
        latency_ms=response.timings.total_ms,
    )
    return response
