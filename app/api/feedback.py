from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.errors import PyMongoError

from app.core.config import Settings, get_settings
from app.models.feedback import FeedbackRecord, FeedbackRequest, FeedbackReview
from app.services import feedback

router = APIRouter()
ConfiguredSettings = Annotated[Settings, Depends(get_settings)]


@router.post("/feedback", status_code=201)
async def submit(request: FeedbackRequest, settings: ConfiguredSettings) -> FeedbackRecord:
    try:
        return await feedback.submit_feedback(request, settings)
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Feedback store unavailable") from None


@router.get("/feedback")
async def list_recent(
    settings: ConfiguredSettings, limit: Annotated[int, Query(ge=1, le=100)] = 20
) -> list[FeedbackRecord]:
    try:
        return await feedback.list_recent(settings, limit)
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Feedback store unavailable") from None


@router.post("/feedback/{feedback_id}/review")
async def review(
    feedback_id: UUID, request: FeedbackReview, settings: ConfiguredSettings
) -> dict[str, str]:
    try:
        updated = await feedback.review(feedback_id, request, settings)
    except PyMongoError:
        raise HTTPException(status_code=503, detail="Feedback store unavailable") from None
    if not updated:
        raise HTTPException(status_code=409, detail="Feedback is absent or already reviewed")
    return {"status": request.status}
