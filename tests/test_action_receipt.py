"""Regression tests for action receipt."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.models.validation import ServiceRequestReceipt


def receipt(**changes) -> dict:
    """Provide receipt for the action receipt scenario.

    Args:
        changes: Input mutations used to exercise validation boundaries.

    Returns:
        Named values describing the documented operation or diagnostic outcome.
    """
    return {
        "service_request_id": "NXSR-000001",
        "customer_id": "NXC-0010",
        "request_type": "CALLBACK",
        "status": "RECEIVED",
        "created_at": "2026-10-27T00:00:00Z",
        **changes,
    }


def test_contract_allows_an_omitted_optional_loan_on_a_customer_receipt() -> None:
    """Verify contract allows an omitted optional loan on a customer receipt."""
    parsed = ServiceRequestReceipt.model_validate_json(json.dumps(receipt()), strict=True)
    assert parsed.loan_account_id is None


@pytest.mark.parametrize(
    "changes", [{"service_request_id": " "}, {"created_at": "2026-10-27T00:00:00"}]
)
def test_receipt_requires_a_real_identifier_and_timezone(changes: dict) -> None:
    """Verify receipt requires a real identifier and timezone.

    Args:
        changes: Input mutations used to exercise validation boundaries.
    """
    with pytest.raises(ValidationError):
        ServiceRequestReceipt.model_validate_json(
            json.dumps(receipt(loan_account_id=None, **changes)), strict=True
        )
