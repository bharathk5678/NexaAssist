from __future__ import annotations

from uuid import UUID

from pymongo.errors import DuplicateKeyError

from app.core.config import Settings
from app.database.mongo import _database
from app.models.feedback import FeedbackRecord, FeedbackReview


def save_feedback(record: FeedbackRecord, settings: Settings) -> FeedbackRecord | None:
    collection = _database(settings)[settings.mongodb_feedback_collection]
    query = {"_id": str(record.feedback_id), "institution": settings.institution}
    try:
        previous = collection.find_one_and_update(
            query,
            {
                "$setOnInsert": {
                    "_id": str(record.feedback_id),
                    "institution": settings.institution,
                    **record.model_dump(mode="json"),
                }
            },
            upsert=True,
        )
    except DuplicateKeyError:
        previous = collection.find_one(query)
        if previous is None:
            raise
    if previous is None:
        return None
    return FeedbackRecord.model_validate(
        {key: value for key, value in previous.items() if key not in {"_id", "institution"}}
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
