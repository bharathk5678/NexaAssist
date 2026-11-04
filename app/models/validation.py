"""Define trusted access, supported service proposals and verified banking receipts."""

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
    """Validated service request details contract.

    Attributes:
        request_type: Supported service-request category selected for the operation.
        loan_account_id: Existing loan account selected for ownership and eligibility checks.
        notes: Optional bounded service-request notes, screened before model/tool execution.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_type: ServiceRequestType
    loan_account_id: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=500)


class ServiceRequestProposal(ServiceRequestDetails):
    """Service Request Proposal used by validation.

    Attributes:
        customer_id: Synthetic customer identifier within the authorized scope.
    """

    customer_id: str = Field(pattern=r"^NXC-[0-9]{4}$")

    @model_validator(mode="after")
    def required_loan_is_present(self) -> ServiceRequestProposal:
        """Require an owned loan selection for certificate and opt-in proposals.

        Raises:
            ValueError: This service-request proposal requires a selected loan.
        """
        if (
            self.request_type in ("OPT_IN_CIR_2026_07_PART_PREPAY", "INTEREST_CERTIFICATE")
            and self.loan_account_id is None
        ):
            raise ValueError("This service-request proposal requires a selected loan")
        return self


class ValidationAccess(BaseModel):
    """Server-issued scope, never populated from model or request-body claims.

    Attributes:
        customer_ids: Customer identifiers this configured principal may access.
        principal_id: Unique configured staff identity; independent of customer identifiers.
        can_approve: Whether this configured principal may decide another owner's proposal.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    customer_ids: frozenset[str]
    principal_id: str = "training"
    can_approve: bool = False


class AgentPrincipal(BaseModel):
    """Trusted API-key identity; credentials and entitlements never come from a request body.

    Attributes:
        principal_id: Unique configured staff identity; independent of customer identifiers.
        token: Secret bearer credential matched to this named principal.
        customer_ids: Customer identifiers this configured principal may access.
        can_approve: Whether this configured principal may decide another owner's proposal.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    principal_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    token: SecretStr = Field(min_length=32)
    customer_ids: frozenset[Annotated[str, Field(pattern=r"^NXC-[0-9]{4}$")]] = Field(min_length=1)
    can_approve: bool = False


class CustomerAccounts(BaseModel):
    """Validated customer accounts contract.

    Attributes:
        customer_id: Synthetic customer identifier within the authorized scope.
        accounts: Current non-loan account records returned by the banking integration.
        loans: Current customer loan records supplied by the banking integration.
    """

    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(pattern=r"^NXC-[0-9]{4}$")
    accounts: list[dict[str, Any]]
    loans: list[dict[str, Any]]


class LoanReference(BaseModel):
    """Validated loan reference contract.

    Attributes:
        loan_account_id: Existing loan account selected for ownership and eligibility checks.
        product_id: Explicit product scope, when required or supplied.
    """

    model_config = ConfigDict(extra="forbid")

    loan_account_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)


class LoanEligibilityFacts(LoanReference):
    """Only the fields needed for circular 5.2; other banking data is discarded.

    Attributes:
        policy_doc: Bank-reported policy instrument associated with the selected loan.
        version_id: Banking product-policy version used by the circular eligibility rule.
        sanction_date: Bank-reported loan sanction date used by the circular eligibility rule.
        circ_2026_07_part_prepay_opt_in: Current bank-reported circular opt-in status, when available.
    """

    policy_doc: str
    version_id: str
    sanction_date: date
    circ_2026_07_part_prepay_opt_in: bool | None = None


class ValidationEvidence(BaseModel):
    """Validated validation evidence contract.

    Attributes:
        citation: Document version, clause and effective date identifying this evidence.
        quote: Exact contiguous evidence text supporting the cited answer.
    """

    model_config = ConfigDict(extra="forbid")

    citation: Citation
    quote: str = Field(min_length=1)


class ValidationResult(BaseModel):
    """Validated validation result contract.

    Attributes:
        decision: Reviewer decision bound to the exact retained proposal hash.
        reason: Safe explanation of a validation or metric availability outcome.
        evidence: Retained retrieval results and complete applicable amendments.
        proposal: Exact allowed service-request payload; absent for other decisions.
        requires_approval: Always true: validation alone never authorizes an external write.
    """

    model_config = ConfigDict(extra="forbid")

    decision: Literal["allowed", "blocked", "insufficient_evidence", "unavailable"]
    reason: str
    evidence: list[ValidationEvidence] = Field(default_factory=list)
    proposal: ServiceRequestProposal | None = None
    requires_approval: Literal[True] = True

    @model_validator(mode="after")
    def proposal_matches_decision(self) -> ValidationResult:
        """Require evidence and a proposal exactly when validation is allowed.

        Raises:
            ValueError: An allowed proposal requires policy evidence.
        """
        if (self.decision == "allowed") != (self.proposal is not None):
            raise ValueError("Only an allowed decision can carry a proposal")
        if self.decision == "allowed" and not self.evidence:
            raise ValueError("An allowed proposal requires policy evidence")
        return self


class ServiceRequestReceipt(BaseModel):
    """Validated service request receipt contract.

    Attributes:
        customer_id: Synthetic customer identifier within the authorized scope.
        request_type: Supported service-request category selected for the operation.
        loan_account_id: Existing loan account selected for ownership and eligibility checks.
        status: HTTP or workflow status used by the scenario.
        created_at: Timezone-aware creation timestamp of the saved run or receipt.
    """

    model_config = ConfigDict(extra="forbid")

    service_request_id: str = Field(min_length=1)
    customer_id: str = Field(pattern=r"^NXC-[0-9]{4}$")
    request_type: ServiceRequestType
    loan_account_id: str | None = None
    status: Literal["RECEIVED"]
    created_at: datetime

    @model_validator(mode="after")
    def valid_receipt_identity_and_time(self) -> ServiceRequestReceipt:
        """Reject blank receipt identities and timestamps without a timezone.

        Raises:
            ValueError: Banking receipt requires a nonblank ID and timezone-aware timestamp.
        """
        if not self.service_request_id.strip() or self.created_at.utcoffset() is None:
            raise ValueError("Banking receipt requires a nonblank ID and timezone-aware timestamp")
        return self


class SubmittedServiceRequest(BaseModel):
    """Validated submitted service request contract.

    Attributes:
        status: HTTP or workflow status used by the scenario.
        evidence: Retained retrieval results and complete applicable amendments.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["submitted"] = "submitted"
    service_request: ServiceRequestReceipt
    evidence: list[ValidationEvidence]
