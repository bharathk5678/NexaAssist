"""Submit exact authorized proposals and verify matching banking receipts."""

from __future__ import annotations

import httpx
from ddtrace import tracer

from app.models.agent import AgentSubmissionRequest
from app.models.validation import (
    ServiceRequestProposal,
    ServiceRequestReceipt,
    SubmittedServiceRequest,
    ValidationAccess,
    ValidationResult,
)


@tracer.wrap(name="service_request.submit", resource="createServiceRequest")
async def submit_service_request(
    request: AgentSubmissionRequest,
    validation: ValidationResult,
    client: httpx.AsyncClient,
    access: ValidationAccess,
    idempotency_key: str,
) -> SubmittedServiceRequest:
    """Submit the exact allowed proposal and verify the banking receipt identity.

    Args:
        request: Validated request retaining the caller's explicit scope and action details.
        validation: Retained policy and banking validation for the exact proposed action.
        client: HTTP client configured for the required upstream service.
        access: Server-issued principal identity, customer entitlements and review permission.
        idempotency_key: Persisted operation key reused for the unchanged banking submission.

    Returns:
        Validated matching bank receipt together with retained policy evidence.

    Raises:
        ValueError: Banking receipt differs from the submitted proposal.
        httpx.HTTPError: Submission fails or its receipt cannot be confirmed.
        ValidationError: The banking receipt does not satisfy its strict response schema.
    """
    expected = ServiceRequestProposal(
        customer_id=request.customer_id, **request.action_details.model_dump()
    )
    if (
        request.customer_id not in access.customer_ids
        or validation.decision != "allowed"
        or validation.proposal != expected
    ):
        raise ValueError("Submission requires an authorized, exact validated proposal")
    response = await client.post(
        "v1/service-requests",
        json=expected.model_dump(mode="json"),
        headers={"Idempotency-Key": idempotency_key},
    )
    response.raise_for_status()
    receipt = ServiceRequestReceipt.model_validate_json(response.content, strict=True)
    if (
        receipt.customer_id != expected.customer_id
        or receipt.request_type != expected.request_type
        or receipt.loan_account_id != expected.loan_account_id
    ):
        raise ValueError("Banking receipt differs from the submitted proposal")
    return SubmittedServiceRequest(service_request=receipt, evidence=validation.evidence)
