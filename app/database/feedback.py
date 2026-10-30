"""Persist idempotent feedback and protected review updates."""

from __future__ import annotations

from uuid import UUID

from pymongo.errors import DuplicateKeyError

from app.core.config import Settings
from app.database.mongo import _database
from app.models.feedback import FeedbackRecord, FeedbackReview


def save_feedback(record: FeedbackRecord, settings: Settings) -> FeedbackRecord | None:
    """Persist feedback idempotently without overwriting a prior submission.

    Args:
        record: Retained evaluation case, generated answer and supporting source identities.
        settings: Validated application configuration for this operation.

    Returns:
        FeedbackRecord | None value produced by this operation.
    """
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
    """Return recent feedback records for authorized review.

    Args:
        settings: Validated application configuration for this operation.
        limit: Limit supplied by the caller.

    Returns:
        Ordered results produced by the documented operation.
    """
    rows = (
        _database(settings)[settings.mongodb_feedback_collection]
        .find({"institution": settings.institution}, {"_id": 0, "institution": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    return [FeedbackRecord.model_validate(row) for row in rows]


def review_feedback(feedback_id: UUID, review: FeedbackReview, settings: Settings) -> bool:
    """Update the selected feedback review within the configured institution.

    Args:
        feedback_id: Feedback id identifying the scoped record.
        review: Review supplied by the caller.
        settings: Validated application configuration for this operation.

    Returns:
        Whether the documented condition or operation succeeded.
    """
    result = _database(settings)[settings.mongodb_feedback_collection].update_one(
        {"_id": str(feedback_id), "institution": settings.institution, "status": "pending"},
        {"$set": review.model_dump(mode="json")},
    )
    return result.modified_count == 1
