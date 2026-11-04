"""Resolve named agent scopes and protected feedback-review credentials."""

from __future__ import annotations

from secrets import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import AgentSettings, Settings, get_agent_settings, get_settings
from app.models.validation import ValidationAccess

reviewer_bearer = HTTPBearer(auto_error=False, scheme_name="FeedbackReviewer")
validator_bearer = HTTPBearer(auto_error=False, scheme_name="AgentValidator")


def get_validation_access(
    settings: Annotated[AgentSettings, Depends(get_agent_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(validator_bearer)],
) -> ValidationAccess | None:
    """Resolve a bearer credential into server-owned identity and customer entitlements.

    Args:
        credentials: Bearer credentials supplied at the authentication boundary.

    Returns:
        Matched server-owned access, or None when no configured credential matches.
    """
    if credentials is None:
        return None
    for principal in settings.agent_principals:
        if compare_digest(
            credentials.credentials.encode(), principal.token.get_secret_value().encode()
        ):
            return ValidationAccess(
                customer_ids=principal.customer_ids,
                principal_id=principal.principal_id,
                can_approve=principal.can_approve,
            )
    # shortcut: legacy shared training token; named identities are required for human approval.
    if settings.agent_validation_token is None:
        return None
    if not compare_digest(
        credentials.credentials.encode(),
        settings.agent_validation_token.get_secret_value().encode(),
    ):
        return None
    return ValidationAccess(customer_ids=settings.agent_allowed_customer_ids)


def require_reviewer(
    settings: Annotated[Settings, Depends(get_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(reviewer_bearer)],
) -> None:
    """Require the configured feedback-review credential before serving protected routes.

    Args:
        credentials: Bearer credentials supplied at the authentication boundary.

    Raises:
        HTTPException: Reviewer credentials required.
    """
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
