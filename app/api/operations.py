from __future__ import annotations

from fastapi import APIRouter

from app.services.retrieval import retrieval_metrics

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics")
async def metrics() -> dict[str, int | float]:
    return {
        "retrieval_requests_total": retrieval_metrics["requests"],
        "retrieval_errors_total": retrieval_metrics["errors"],
        "retrieval_empty_total": retrieval_metrics["empty"],
        "retrieval_latency_ms_total": retrieval_metrics["latency_us_total"] / 1000,
    }
