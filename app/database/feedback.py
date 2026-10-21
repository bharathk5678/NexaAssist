from __future__ import annotations

from uuid import UUID

from app.core.config import Settings
from app.database.mongo import _database
from app.models.feedback import FeedbackRecord, FeedbackReview


def save_feedback(record: FeedbackRecord, settings: Settings) -> None:
    _database(settings)[settings.mongodb_feedback_collection].insert_one(
        {
            "_id": str(record.feedback_id),
            "institution": settings.institution,
            **record.model_dump(mode="json"),
        }
    )


def list_feedback(settings: Settings, limit: int) -> list[FeedbackRecord]:
    rows = (
        _database(settings)[settings.mongodb_feedback_collection]
        .find({"institution": settings.institution}, {"_id": 0, "institution": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    return [FeedbackRecord.model_validate(row) for row in rows]


def review_feedback(feedback_id: UUID, review: FeedbackReview, settings: Settings) -> bool:
    result = _database(settings)[settings.mongodb_feedback_collection].update_one(
        {"_id": str(feedback_id), "institution": settings.institution, "status": "pending"},
        {"$set": review.model_dump(mode="json")},
    )
    return result.modified_count == 1
