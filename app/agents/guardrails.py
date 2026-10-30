"""Screen request text for sensitive identifiers and instruction overrides."""

from __future__ import annotations

import re

from app.models.agent import AgentRequest

INJECTION = re.compile(
    r"ignore\s+(?:(?:all|the)\s+)?(?:previous|prior|system)\s+instructions"
    r"|(?:reveal|print|show)\s+(?:the\s+)?system\s+prompt"
    r"|(?:bypass|disable|skip)\s+(?:(?:the|human)\s+)?(?:approval|validator|validation|kyc)",
    re.IGNORECASE,
)
SENSITIVE = re.compile(
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b|\bsk-[A-Za-z0-9_-]{20,}\b"
    r"|\b(?:[0-9][ -]?){12,19}\b"
)


def unsafe_input(request: AgentRequest) -> bool:
    """Conservative input screening; deterministic authorization still guards every action.

    Args:
        request: Validated request retaining the caller's explicit scope and action details.

    Returns:
        Whether the documented condition or operation succeeded.
    """
    notes = request.action_details.notes if request.action_details is not None else None
    text = request.query + "\n" + (notes or "")
    return bool(INJECTION.search(text) or SENSITIVE.search(text))
