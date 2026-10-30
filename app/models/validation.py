from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from app.models.retrieval import Citation

type ServiceRequestType = Literal[
    "STATEMENT_COPY",
    "CALLBACK",
    "RE_KYC_REMINDER",
    "OPT_IN_CIR_2026_07_PART_PREPAY",
    "INTEREST_CERTIFICATE",
]


class ServiceRequestDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_type: ServiceRequestType
    loan_account_id: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=500)


class ServiceRequestProposal(ServiceRequestDetails):
    customer_id: str = Field(pattern=r"^NXC-[0-9]{4}$")

    @model_validator(mode="after")
    def required_loan_is_present(self) -> ServiceRequestProposal:
        if (
            self.request_type in ("OPT_IN_CIR_2026_07_PART_PREPAY", "INTEREST_CERTIFICATE")
            and self.loan_account_id is None
        ):
            raise ValueError("This service-request proposal requires a selected loan")
        return self


class ValidationAccess(BaseModel):
    """Server-issued scope, never populated from model or request-body claims."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    customer_ids: frozenset[str]
    principal_id: str = "training"
    can_approve: bool = False


class AgentPrincipal(BaseModel):
    """Trusted API-key identity; credentials and entitlements never come from a request body."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    principal_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    token: SecretStr = Field(min_length=32)
    customer_ids: frozenset[Annotated[str, Field(pattern=r"^NXC-[0-9]{4}$")]] = Field(min_length=1)
    can_approve: bool = False


class CustomerAccounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(pattern=r"^NXC-[0-9]{4}$")
    accounts: list[dict[str, Any]]
    loans: list[dict[str, Any]]


class LoanReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loan_account_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)


class LoanEligibilityFacts(LoanReference):
    """Only the fields needed for circular 5.2; other banking data is discarded."""

    policy_doc: str
    version_id: str
    sanction_date: date
    circ_2026_07_part_prepay_opt_in: bool | None = None


class ValidationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation: Citation
    quote: str = Field(min_length=1)


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["allowed", "blocked", "insufficient_evidence", "unavailable"]
    reason: str
    evidence: list[ValidationEvidence] = Field(default_factory=list)
    proposal: ServiceRequestProposal | None = None
    requires_approval: Literal[True] = True

    @model_validator(mode="after")
    def proposal_matches_decision(self) -> ValidationResult:
        if (self.decision == "allowed") != (self.proposal is not None):
            raise ValueError("Only an allowed decision can carry a proposal")
        if self.decision == "allowed" and not self.evidence:
            raise ValueError("An allowed proposal requires policy evidence")
        return self


class ServiceRequestReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_request_id: str = Field(min_length=1)
    customer_id: str = Field(pattern=r"^NXC-[0-9]{4}$")
    request_type: ServiceRequestType
    loan_account_id: str | None = None
    status: Literal["RECEIVED"]
    created_at: datetime

    @model_validator(mode="after")
    def valid_receipt_identity_and_time(self) -> ServiceRequestReceipt:
        if not self.service_request_id.strip() or self.created_at.utcoffset() is None:
            raise ValueError("Banking receipt requires a nonblank ID and timezone-aware timestamp")
        return self


class SubmittedServiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["submitted"] = "submitted"
    service_request: ServiceRequestReceipt
    evidence: list[ValidationEvidence]
