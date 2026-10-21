from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog
from ddtrace.llmobs import LLMObs

from app.core.config import Settings
from app.database import feedback as database
from app.models.feedback import FeedbackRecord, FeedbackRequest, FeedbackReview


async def submit_feedback(request: FeedbackRequest, settings: Settings) -> FeedbackRecord:
    record = FeedbackRecord(
        **request.model_dump(), feedback_id=uuid4(), created_at=datetime.now(UTC)
    )
    await asyncio.to_thread(database.save_feedback, record, settings)
    if LLMObs.enabled and request.response.datadog_span_id is not None:
        try:
            LLMObs.submit_feedback(
                label="thumbs",
                metric_type="boolean",
                value=request.helpful,
                submitter={"id": str(request.submitter_id), "type": "end_user"},
                span_id=request.response.datadog_span_id,
                agent_service=settings.dd_service,
                assessment="pass" if request.helpful else "fail",
                reasoning=request.correction.strip() or None,
                tags={"feedback_id": str(record.feedback_id)},
            )
        except Exception as exc:  # noqa: BLE001 - feedback is already saved for review
            structlog.get_logger().warning(
                "feedback_datadog_publish_failed",
                feedback_id=str(record.feedback_id),
                error_type=type(exc).__name__,
            )
    return record


async def list_recent(settings: Settings, limit: int) -> list[FeedbackRecord]:
    return await asyncio.to_thread(database.list_feedback, settings, limit)


async def review(feedback_id: UUID, request: FeedbackReview, settings: Settings) -> bool:
    return await asyncio.to_thread(database.review_feedback, feedback_id, request, settings)
