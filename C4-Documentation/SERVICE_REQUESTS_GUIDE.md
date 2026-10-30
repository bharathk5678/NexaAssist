# Service requests: operator guide and approval troubleshooting

Verified 30 October 2026 against the working tree, all 27 bundled customer records,
and 27 read-only account responses from the running banking mock. Scope: the local
training deployment. No live proposal was approved, rejected, retried or submitted.

## 1. Resolve the HTTP 403 first

**Prepare with the owner credential. Decide with a different reviewer credential.**
Approve and reject share the same authorization gate. The reviewer must have
`can_approve=true`, access to the run's customer, and a different `principal_id`
from the identity that created the run. The word `reviewer` alone does not grant
permission; the server's configuration does.

The current local configuration has:

| Identity | Can decide? | Customer scope |
|---|---|---|
| owner | No | NXC-0010 |
| reviewer | Yes, for another identity's run | NXC-0010 |

The latest inspected run was created by `reviewer`; it cannot be decided by that
same reviewer. The configured `owner` cannot decide it either. The three most
recent inspected runs were expired and had no recorded approval or banking attempt.
Use a fresh owner-created proposal for these expired, never-submitted examples.
Do not apply that advice to an uncertain bank submission; see recovery below.

### Exact UI sequence

1. Keep RAG FastAPI (8000), banking mock (8080), Agent FastAPI (8001), and
   Streamlit (8501) running. See [startup commands](../README.md#streamlit-and-endpoint-coverage).
2. Open **Service requests**. Paste the raw **owner token** into **Agent credential**.
   Do not include `Bearer`, `owner:`, quotes, or whitespace. Tokens identify staff
   principals, not customers. Never use the banking token or feedback reviewer token here.
3. Use customer `NXC-0010`. Start with `CALLBACK`, loan blank, notes blank,
   product blank, policy date `2026-10-30`. Click **Prepare for approval**.
4. Confirm status `pending_approval`; copy the returned **Saved run ID**. A `201`
   only means the run was created: inspect its status for clarification or blockers.
5. Replace **Agent credential** with the raw **reviewer token**. Commit the edit
   with Enter or by leaving the field. Changing credentials intentionally clears
   the loaded proposal.
6. Enter/preserve the exact saved ID and click **Load saved run**. Do not click
   **Prepare for approval** while using the reviewer credential.
7. Inspect the proposal and policy evidence, choose **approve** or **reject**, tick
   **I reviewed this exact proposal and its policy evidence**, and click
   **Submit reviewer decision**. The radio defaults to **reject**.
8. Complete the handoff before the displayed expiry. The default 900 seconds starts
   when the run is created, including preparation time. ISO timestamps may be UTC.
9. Reject returns `rejected` without a bank write. Approve resumes policy/account
   revalidation and may submit to the bank. `submitted` plus bank `RECEIVED` is
   receipt acceptance, not completion of the requested work.

Using two browser sessions is possible: the owner keeps the preparation session,
and the reviewer enters the saved run ID in their own session. Both still need
separate identities and access to the same customer.

### Inspect roles and scopes without displaying secrets

To copy an existing token on macOS, run **one** command at the appropriate step:

```bash
# Copy owner token before Prepare for approval
uv run --no-sync --env-file .env python -c 'from app.core.config import get_agent_settings; print(next(p.token.get_secret_value() for p in get_agent_settings().agent_principals if p.principal_id == "owner"))' | pbcopy

# Copy reviewer token before Load saved run and the reviewer decision
uv run --no-sync --env-file .env python -c 'from app.core.config import get_agent_settings; print(next(p.token.get_secret_value() for p in get_agent_settings().agent_principals if p.principal_id == "reviewer"))' | pbcopy
```

No token is displayed: `pbcopy` puts it on the local clipboard. Paste with **⌘V**
in **Agent credential**. Running the second command replaces the clipboard's first
value. These commands retrieve existing credentials; they do not create new ones.

Run from the repository root. This reads configuration only:

```bash
uv run --no-sync --env-file .env python - <<'PYCODE'
from app.core.config import get_agent_settings
for p in get_agent_settings().agent_principals:
    print(p.principal_id, 'can_approve=', p.can_approve,
          'customers=', sorted(p.customer_ids))
PYCODE
```

To identify which local credential you have, without echoing it:

```bash
uv run --no-sync --env-file .env python - <<'PYCODE'
from getpass import getpass
from secrets import compare_digest
from app.core.config import get_agent_settings
entered = getpass('Paste the raw agent token (hidden): ').strip()
match = next((p for p in get_agent_settings().agent_principals
              if compare_digest(entered, p.token.get_secret_value())), None)
if match is None:
    print('No matching named principal in this configuration.')
else:
    print('Identity:', match.principal_id)
    print('Can approve/reject:', match.can_approve)
    print('Customer scope:', sorted(match.customer_ids))
PYCODE
```

This checks the fresh command's environment, not the already-running API's cached
settings. Restart Agent FastAPI after changing `.env`. An exported variable or a
service manager's environment can override `.env`; use the same configuration for
both the command and the API. Never paste tokens into a chat or commit them.
The existing `app/get_bearer_token.py` generates credentials only when none exist;
it deliberately refuses to overwrite existing identities.

## 2. Customer access configuration

Adding a customer record or entering its ID in the UI does not grant access.
An administrator must include the intended IDs in **both** the owner's and the
reviewer's existing `AGENT_PRINCIPALS` entries. For the two discussed customers,
the fragment in each entry would be:

```json
"customer_ids": ["NXC-0002", "NXC-0010"]
```

Keep `owner.can_approve=false`, `reviewer.can_approve=true`, distinct principal IDs,
and distinct secret tokens (at least 32 characters). Restart the Agent API, which
caches settings. This guide does not grant access to NXC-0002 or any other customer.
Authorize only the customers needed for the exercise; do not use a wildcard.
The legacy `AGENT_VALIDATION_TOKEN` is not accepted for durable runs.

Active tokens were duplicated in `.env.example`; those duplicate assignments have
been removed. `.env` and active tokens were left unchanged. If that example was
shared, treat those values as exposed and coordinate rotation. Changing the banking
identity can invalidate safe retries of existing uncertain operations; reconcile
those operations before rotating or resetting the mock.

## 3. Requirements for all five use cases

All rows require a configured owner and distinct reviewer with customer access,
valid policy evidence for the selected date, and a reachable banking accounts API.
Notes are optional, at most 500 characters, and screened for sensitive identifiers
and instruction overrides. Do not add KYC, income or credit criteria that the
implemented validator does not require.

| Request type | Loan account | Product/date and evidence | Expected outcome |
|---|---|---|---|
| STATEMENT_COPY | Optional; blank for customer-level exercise | POL-OPS-001 v1.0 clause 5.1, date on/after 2025-01-01 | Request for a copy; no statement file generated |
| CALLBACK | Optional; normally blank | Same operations evidence/date | Callback request receipt |
| RE_KYC_REMINDER | Optional; normally blank | Same operations evidence/date | Reminder request; does not perform KYC |
| INTEREST_CERTIFICATE | Required, must belong to customer | Same operations evidence/date; if product selected it must match loan | Certificate request receipt; no PDF or download generated |
| OPT_IN_CIR_2026_07_PART_PREPAY | Required, eligible home loan | Product NEXA-HL; date on/after 2026-07-01; complete CIR-2026-07 v1.0 clause 5.2 | Opt-in request receipt; mock does not itself change the opt-in flag |

For **any** type, supplying a loan makes ownership validation mandatory. For
non-opt-in requests, an optional selected product is checked against the supplied
loan. Clear an unrelated product left in the sidebar. The policy lookup for the
four ordinary request types intentionally searches bank-wide operations policy.
For certificate/opt-in, missing loan details may produce `needs_clarification`
before the validator runs. A loan application is not an existing loan account.

### Worked certificate request

Use owner token, customer `NXC-0010`, type `INTEREST_CERTIFICATE`, loan
`NXL-HL-0010`, product blank or `NEXA-HL`, date `2026-10-30`. Prepare, save the ID,
switch to reviewer, load the run, and decide. No financial year or certificate
rendering pipeline is modeled in the current request schema.

### Worked opt-in request and counterexamples

Use the same customer/loan, type `OPT_IN_CIR_2026_07_PART_PREPAY`, product
`NEXA-HL`, and date `2026-10-30`. The loan must be POL-HL-V3 / NHL-2025-10,
sanctioned strictly before 2026-07-01, and currently not opted in.
NXC-0001 has an older policy; NXC-0016 has a later version/sanction;
NXC-0023 is already opted in. These are expected blocked examples once customer
access is explicitly configured. NXC-0002 has no existing loan, so use a general
request type for it after granting the intended scope; it cannot supply a genuine
certificate or opt-in loan from the current catalog.

## 4. Complete customer and use-case matrix

This is a 30 October snapshot, not a promise that later mutable banking facts or
retrieved policy will match. `General` covers STATEMENT_COPY, CALLBACK and
RE_KYC_REMINDER with **loan blank**. Eligibility columns assume correct scope and
fixed valid evidence; configured access is a separate column. `Yes` still needs
reviewer approval and revalidation. All IDs are synthetic, with no personal details.

| Customer | Both identities currently scoped? | Existing loan / product | General (3 types) | Interest certificate | Opt-in eligibility |
|---|---|---|---|---|---|
| NXC-0001 | No — needs explicit scope | NXL-HL-0001 / NEXA-HL | Yes | Yes — use listed loan | Policy/version or sanction outside rule |
| NXC-0002 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |
| NXC-0003 | No — needs explicit scope | NXL-PL-0003 / NEXA-PL | Yes | Yes — use listed loan | Not a home loan |
| NXC-0004 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |
| NXC-0005 | No — needs explicit scope | NXL-AL-0005 / NEXA-AL | Yes | Yes — use listed loan | Not a home loan |
| NXC-0006 | No — needs explicit scope | NXL-LAP-0006 / NEXA-LAP | Yes | Yes — use listed loan | Not a home loan |
| NXC-0007 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |
| NXC-0008 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |
| NXC-0009 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |
| NXC-0010 | Yes | NXL-HL-0010 / NEXA-HL | Yes | Yes — use listed loan | Yes |
| NXC-0011 | No — needs explicit scope | NXL-HL-0011 / NEXA-HL | Yes | Yes — use listed loan | Policy/version or sanction outside rule |
| NXC-0012 | No — needs explicit scope | NXL-HL-0012 / NEXA-HL | Yes | Yes — use listed loan | Policy/version or sanction outside rule |
| NXC-0013 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |
| NXC-0014 | No — needs explicit scope | NXL-PL-0014 / NEXA-PL | Yes | Yes — use listed loan | Not a home loan |
| NXC-0015 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |
| NXC-0016 | No — needs explicit scope | NXL-HL-0016 / NEXA-HL | Yes | Yes — use listed loan | Policy/version or sanction outside rule |
| NXC-0017 | No — needs explicit scope | NXL-AL-0017 / NEXA-AL | Yes | Yes — use listed loan | Not a home loan |
| NXC-0018 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |
| NXC-0019 | No — needs explicit scope | NXL-PL-0019 / NEXA-PL | Yes | Yes — use listed loan | Not a home loan |
| NXC-0020 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |
| NXC-0021 | No — needs explicit scope | NXL-HL-0021 / NEXA-HL | Yes | Yes — use listed loan | Policy/version or sanction outside rule |
| NXC-0022 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |
| NXC-0023 | No — needs explicit scope | NXL-HL-0023 / NEXA-HL | Yes | Yes — use listed loan | Already opted in |
| NXC-0024 | No — needs explicit scope | NXL-LAP-0024 / NEXA-LAP | Yes | Yes — use listed loan | Not a home loan |
| NXC-0025 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |
| NXC-0026 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |
| NXC-0027 | No — needs explicit scope | None | Yes | No existing loan | No existing loan |

The catalog contains **27 customers and 14 loans**: 7 home, 3 personal, 2 auto,
and 2 loan-against-property accounts. With access and fixed valid evidence, the
three general types cover all 27 customers, certificates cover the 14 customers
with loans, and the opt-in rule permits only NXC-0010. Current configured access
allows only NXC-0010 through the full owner/reviewer handoff.

## 5. Error and recovery guide

| Result | Meaning / next step |
|---|---|
| 403 on prepare | Token not a configured named identity, or requested customer outside creator scope |
| 403 on approve/reject | Token not named; caller lacks can_approve; caller created the run; or the saved owner's access was revoked. Inspect the API response detail to distinguish these |
| 404 on load/decision | Unknown run or deliberately hidden because caller lacks customer/owner/reviewer visibility; a scoped reviewer must load another owner's run |
| 409 on decision | Expired/stale hash or wrong run state; alternatively another operation holds the run lease. Reload and inspect before acting |
| 422 | Invalid schema or sensitive/instruction-override notes; fix inputs, do not bypass guards |
| 503 storage | Check Atlas connectivity, permissions, checkpoint collections/index setup |
| 503 other / timeout | Check Agent logs and RAG/banking dependencies; load the saved run before choosing recovery |
| needs_clarification | Supply missing date/customer/action/loan/product as applicable and prepare a complete proposal |
| blocked / insufficient_evidence | Read validation reason and evidence; correct loan/product/date or corpus, do not force approval |
| pending_approval | No bank write yet; perform reviewer handoff before expiry |
| rejected | Terminal decision; no bank write; a changed request needs a new proposal |
| unconfirmed | Bank may have received it. Load and retry the **same run**, preserving payload and key; do not prepare a replacement |
| submitted + RECEIVED | Accepted receipt, not downstream fulfillment. Do not resubmit |

For 403, capture the failing path, run ID, HTTP status and safe API detail, not
Authorization headers. The UI currently groups multiple 403 causes into one
message and shows decision controls without knowing the caller's server-side role.
A proposal being visible does not mean that the current credential can decide it.
The Datadog missing-ASGI-context warning is a telemetry issue; it is not the
source of this authorization decision. Health endpoints prove process liveness,
not dependency readiness.

The retry path is for an already approved, unconfirmed **action**, not arbitrary
failed preparation. The service checks banking identity/destination and a safe
retry window of 23 hours from the first attempt. The mock's operation cache lasts
24 hours and exists only in that process. Do not restart/reset it to fix an
uncertain submission; that loses receipts and replay protection.

## 6. Code and function tour

See [the CodeTour artifact](../.tours/feature-explainer-service-requests.tour).
The tour omits `ref` because several implementation files are untracked; CodeTour
must open the current files on disk rather than a revision missing those files.

| Stage | File / functions | Responsibility |
|---|---|---|
| UI | [ui/agent.py](../app/ui/agent.py): agent_workspace, request_run, clear_run | Collect details; attach current raw token; render saved state; clear on identity change |
| Authentication | [api/auth.py](../app/api/auth.py): get_validation_access | Match secret to configured principal, derive role and customer scope |
| Durable routes | [api/agent_runs.py](../app/api/agent_runs.py): named_access, start, read, approve, retry | Reject legacy/unknown identities and delegate to service |
| Persistence/execution | [services/agent_runs.py](../app/services/agent_runs.py): start, _record, _owner, approve, _drive, _graph, _view | Ownership, visibility, expiry/hash, leases, checkpoints, safe execution and retry |
| Wiring | [services/agent.py](../app/services/agent.py): build_workflow, classify, retrieve, validate | LCEL classification plus HTTP retrieval and deterministic validation |
| Graph | [agents/orchestrator.py](../app/agents/orchestrator.py): orchestrator, retrieve, validate, approval, revalidate, action | Route, interrupt for reviewer, recheck, execute |
| RAG boundary | [services/agent_retrieval.py](../app/services/agent_retrieval.py): retrieve_over_http | POST /retrieve to RAG FastAPI, validate response date |
| RAG implementation | [services/retrieval.py](../app/services/retrieval.py): retrieve_policy; [chains/retrieval.py](../app/chains/retrieval.py): build_retrieval_chain | Atlas search, date/scope filters, parent expansion, policy evidence |
| Business rules | [services/validation.py](../app/services/validation.py): validate_service_request, validate_opt_in, _read_accounts, _selected_loan | Evidence, scoped account reads, ownership and opt-in rules |
| Approval fingerprint | [models/agent_run.py](../app/models/agent_run.py): proposal_digest | Hash the request, proposal and evidence together |
| Bank write | [services/service_requests.py](../app/services/service_requests.py): submit_service_request | POST /v1/service-requests with persisted Idempotency-Key, verify exact receipt |
| Banking mock | [mock_server/server.py](../nexa_synthetic_data/api/mock_server/server.py): list_accounts, service_request, run_idempotent | Synthetic account read, receipt storage and request replay |

```mermaid
sequenceDiagram
    participant O as Owner UI
    participant A as Agent FastAPI
    participant R as RAG FastAPI
    participant M as MongoDB
    participant B as Banking mock
    participant V as Reviewer UI
    O->>A: POST /agent/runs (owner token)
    A->>M: Save owner, operation key, graph checkpoints
    A->>R: POST /retrieve
    R->>M: Atlas policy search
    A->>B: GET customer accounts
    A-->>O: pending_approval + run ID + hash
    V->>A: GET /agent/runs/id (different reviewer token)
    A-->>V: Proposal and evidence
    V->>A: POST /agent/runs/id/approval (decision + hash)
    Note over A: Check reviewer role, visibility, different identity, expiry and hash
    alt reject
        A-->>V: rejected; no bank write
    else approve
        A->>R: Refresh evidence
        A->>B: Refresh account facts
        A->>B: POST /v1/service-requests (same persisted key)
        B-->>A: RECEIVED receipt
        A->>M: Persist submitted state
        A-->>V: submitted + receipt
    end
```

## 7. Verification and limits

[Machine-readable matrix verification](service-requests-verification-20261030.json)
records **270 actual validator invocations**: all 27 customers × 5 request types,
once with hypothetical per-customer access and once with the currently configured
owner scope. Fixed valid operations/circular evidence and isolated account HTTP
responses were used. These assertions verify the matrix against the real Python
validator, not live Atlas retrieval, LLM routing or end-to-end banking writes.
All 27 running-bank account endpoints returned 200 and matched catalog loan IDs
and home-loan opt-in flags at the recorded snapshot time.

The targeted suite passed **246 tests** on 30 October 2026. Ruff lint/format and
full app/test mypy also passed. `make check-task` remains blocked by the existing
floor-checker `KeyError`; it was attempted and is not reported as passing.

Existing auth/UI/graph tests are the independent checks for identity switching,
self-approval, expiry, rejection and no-write guarantees. Run:

```bash
uv run --locked --no-sync pytest tests/test_agent_run_auth.py tests/test_agent_ui.py tests/test_agent_runs.py tests/test_validation.py -q
```

Full project gates remain mandatory for application changes. The previous full
suite had 558 passes and one floor-checker failure caused by an untracked copied
source under the presentation directory. Changed-line coverage stalled in recursive
path discovery. Neither is waived by this guide, and constraints were not edited.
Live bank submission and sustained/multi-worker load were not tested. The mock's
in-memory limitation is documented and acceptable only for the single-process demo.

## 8. Dev-team perspectives and synthesis

- **PM:** A reliable owner-to-reviewer walkthrough is the primary outcome. Explicitly
  separate the 27-customer catalog from the one-customer configured demo scope.
- **Architect:** Keep approval, customer entitlements and business-rule eligibility
  separate. Approval remains bound to exact request/evidence and is revalidated.
- **Developer:** Reuse current configuration and helper patterns. No new auth layer
  or bypass is needed; restart the API after config edits and reload after token changes.
- **QA:** Check both approve/reject gates and all customer/type pairs without live
  writes. Do not present fixture-based eligibility as live end-to-end certification.

All four agree that separate identities and matching customer scope are blocking
prerequisites, not optional UX choices. The tension is scope convenience versus
least privilege: this guide documents explicit administrator edits rather than
silently authorizing all 27 customers. A possible future UI improvement is a
server-derived identity/role display; it requires an API contract and is outside
this guide. The current handoff steps need no application change.

## 9. Focused Ponytail review

What this change does: documents the current approval workflow, verifies the full
customer/use-case matrix and adds an anchored tour. It removes duplicate active
tokens from the example configuration without rotating the running identities.
Review scope is the service-request subsystem and these artifacts; expected load
is a single-process local training mock, not production multi-worker banking.

**Must fix / security follow-up**

1. **Active credentials appeared in the shared example** (`.env.example`).
   What this is: the template contained duplicate assignments matching local named
   and banking tokens. Problem: anyone with those values can impersonate the demo
   identities within their scopes. Fix: duplicate values were removed from the
   template; coordinate rotation if it was shared, after reconciling uncertain
   banking operations. If skipped: already copied credentials remain valid.

**Should fix / operator limitation**

2. **Decision controls appear under a creator credential** (`app/ui/agent.py`,
   `agent_workspace`). What this is: pending status drives button visibility.
   Problem: an owner can load a proposal and see approve/reject controls even though
   that identity will always receive 403. Fix: follow the explicit reviewer handoff;
   a later server-derived identity display could prevent confusion without weakening
   authorization. If skipped: repeatable role errors remain possible in the UI.

Verdict: Ship the guide; resolve finding 1 before sharing credentials or deploying.
Not checked: credential rotation, production load, live approvals or banking writes.

## 10. PROJECT-CONTEXT.md preview (not created)

The requested preview for a possible separate shared context file is:

> **Project:** NexaAssist, a synthetic policy and banking service-request training app.
> **Stack:** Python 3.14+, LangChain, MongoDB Atlas, FastAPI, Streamlit, LangGraph,
> Datadog and pytest/RAGAS quality tooling.
> **Phase:** RAG plus durable service requests with distinct human review.
> **Constraints:** Existing CONSTRAINTS.md; strict layers; exact proposal approval;
> scoped identities; no secrets in source; no automatic grants or self-approval.
> **Done:** Operator can prepare, hand off, review and reconcile supported requests;
> customer/type prerequisites and failure cases are documented and verified.

No additional context file was created. This preview contains no tokens or live
customer personal information.
