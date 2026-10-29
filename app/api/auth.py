from __future__ import annotations

from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

reviewer_bearer = HTTPBearer(auto_error=False, scheme_name="FeedbackReviewer")


def require_reviewer(
    settings: Annotated[Settings, Depends(get_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(reviewer_bearer)],
) -> None:
    if settings.feedback_reviewer_token is None:
        raise HTTPException(status_code=503, detail="Feedback review is not configured")
    if credentials is None or not compare_digest(
        credentials.credentials.encode(),
        settings.feedback_reviewer_token.get_secret_value().encode(),
    ):
        raise HTTPException(
            status_code=401,
            detail="Reviewer credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
