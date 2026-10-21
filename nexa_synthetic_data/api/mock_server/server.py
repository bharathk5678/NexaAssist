"""Mock NexaBank case management and core banking API.

Run:  uvicorn server:app --port 8080     (from this directory, after: pip install fastapi uvicorn httpx)
Data: reads ../../customers/customers.json and transactions.csv (override with NEXA_DATA=<dataset root>).
Auth: any non-empty bearer token is accepted. The token is the caller identity for idempotency scoping.
"""
from __future__ import annotations
import csv, hashlib, json, os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

ROOT = Path(os.environ.get("NEXA_DATA", Path(__file__).resolve().parents[2]))
CUSTOMERS = {c["customer_id"]: c for c in json.load(open(ROOT / "customers" / "customers.json"))}
TXNS: dict[str, list[dict]] = {}
for row in csv.DictReader(open(ROOT / "customers" / "transactions.csv")):
    row["amount"] = int(row["amount"]); row["balance_after"] = int(row["balance_after"])
    TXNS.setdefault(row["account_id"], []).append(row)
ACCOUNT_OWNER = {a["account_id"]: cid for cid, c in CUSTOMERS.items() for a in c["accounts"]}

# ---- mutable state (reset with POST /_mock/reset)
CASES: dict[str, dict] = {}
SERVICE_REQUESTS: dict[str, dict] = {}
IDEM: dict[tuple, dict] = {}
# shortcut: mock state is process-local; use shared storage before multiple workers.
FAULTED: set[str] = set()
OPTED_IN: set[str] = {cid for cid, c in CUSTOMERS.items() if c["flags"]["opted_in_cir_2026_07_part_prepay_minimum"]}
COUNTERS = {"case": 0, "note": 0, "esc": 0, "sr": 0}

app = FastAPI(title="NexaBank Case and Core Banking Mock API", version="1.0.0")


class ProblemError(Exception):
    def __init__(self, status, type_, title, detail=None, headers=None, retryable=False):
        self.status, self.type_, self.title, self.detail, self.headers, self.retryable = status, type_, title, detail, headers, retryable


def problem_response(e: ProblemError) -> JSONResponse:
    return JSONResponse({"type": f"https://api.nexabank.example/problems/{e.type_}", "title": e.title, "status": e.status,
                         "detail": e.detail, "retryable": e.retryable}, status_code=e.status, media_type="application/problem+json", headers=e.headers)


@app.exception_handler(ProblemError)
async def _problem_handler(request: Request, exc: ProblemError):
    return problem_response(exc)


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError):
    return problem_response(ProblemError(422, "validation-error", "Request validation failed", json.dumps(exc.errors(), default=str)[:500]))


def auth(request: Request) -> str:
    h = request.headers.get("Authorization", "")
    if not h.startswith("Bearer ") or len(h) < 8:
        raise ProblemError(401, "unauthorized", "Missing or invalid bearer token")
    return h[7:]


def cust(cid: str) -> dict:
    c = CUSTOMERS.get(cid)
    if not c:
        raise ProblemError(404, "not-found", "Customer not found", cid)
    return c


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ reads
@app.get("/v1/customers/{customerId}")
def get_profile(customerId: str, _: str = Depends(auth)):
    c = cust(customerId)
    return {"customer_id": customerId, "profile": c["profile"]}


@app.get("/v1/customers/{customerId}/accounts")
def list_accounts(customerId: str, _: str = Depends(auth)):
    c = cust(customerId)
    loans = [{**l, "circ_2026_07_part_prepay_opt_in": customerId in OPTED_IN} if l["product_id"] == "NEXA-HL" else l for l in c["existing_loans"]]
    return {"customer_id": customerId, "accounts": [a for a in c["accounts"] if a["type"] != "loan"], "loans": loans}


@app.get("/v1/accounts/{accountId}/transactions")
def list_transactions(accountId: str, _: str = Depends(auth), from_: Optional[str] = Query(None, alias="from"), to: Optional[str] = None,
                      limit: int = Query(50, ge=1, le=200), cursor: Optional[str] = None):
    if accountId not in ACCOUNT_OWNER:
        raise ProblemError(404, "not-found", "Account not found", accountId)
    rows = sorted(TXNS.get(accountId, []), key=lambda r: (r["txn_date"], r["txn_id"]), reverse=True)
    if from_: rows = [r for r in rows if r["txn_date"] >= from_]
    if to: rows = [r for r in rows if r["txn_date"] <= to]
    off = int(cursor) if cursor and cursor.isdigit() else 0
    page = rows[off:off + limit]
    return {"items": page, "next_cursor": str(off + limit) if off + limit < len(rows) else None}


@app.get("/v1/customers/{customerId}/kyc-status")
def get_kyc(customerId: str, _: str = Depends(auth)):
    return {"customer_id": customerId, **cust(customerId)["kyc"]}


@app.get("/v1/customers/{customerId}/bureau-summary")
def get_bureau(customerId: str, _: str = Depends(auth)):
    b = dict(cust(customerId)["bureau_summary"]); b.pop("note", None)
    return {"customer_id": customerId, **b}


@app.get("/v1/customers/{customerId}/income")
def get_income(customerId: str, _: str = Depends(auth)):
    c = cust(customerId)
    return {"customer_id": customerId, "disclosed_income": c["disclosed_income"],
            "income_verification": {"status": c["income_verification"]["status"], "method": c["income_verification"]["method"]}}


@app.get("/v1/customers/{customerId}/applications")
def get_apps(customerId: str, _: str = Depends(auth)):
    return {"customer_id": customerId, "applications": cust(customerId)["open_applications"]}


# ------------------------------------------------------------------ idempotent writes
class CaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: str = Field(pattern=r"^NXC-[0-9]{4}$")
    category: Literal["LOAN_ENQUIRY", "KYC_ISSUE", "FEE_WAIVER_REQUEST", "COMPLAINT", "SUSPECTED_FRAUD", "DOCUMENT_ANOMALY", "OTHER"]
    priority: Literal["LOW", "NORMAL", "HIGH"]
    summary: str = Field(min_length=5, max_length=1000)
    related_application_id: Optional[str] = None
    channel: Literal["ASSISTANT"] = "ASSISTANT"


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)


class EscalationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Literal["COMPLAINT", "FEE_WAIVER_OR_SPECIAL_RATE", "SUSPECTED_FRAUD", "HARDSHIP", "KYC_DISCREPANCY", "UPLOAD_WITH_EMBEDDED_INSTRUCTIONS", "OUT_OF_SCOPE_REQUEST"]
    summary: str = Field(min_length=5, max_length=1000)
    preferred_contact: Literal["CALLBACK", "BRANCH_VISIT", "EMAIL"] = "CALLBACK"


class ServiceRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_id: str = Field(pattern=r"^NXC-[0-9]{4}$")
    request_type: Literal["STATEMENT_COPY", "CALLBACK", "RE_KYC_REMINDER", "OPT_IN_CIR_2026_07_PART_PREPAY", "INTEREST_CERTIFICATE"]
    loan_account_id: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=500)


def _hash(payload: BaseModel) -> str:
    return hashlib.sha256(json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


async def run_idempotent(request: Request, token: str, model, handler):
    key = request.headers.get("Idempotency-Key", "")
    if not (16 <= len(key) <= 64):
        raise ProblemError(400, "idempotency-key-required", "Idempotency-Key header is required (16 to 64 characters)")
    try:
        payload = model.model_validate_json(await request.body())
    except ValidationError as e:
        raise ProblemError(422, "validation-error", "Request validation failed", json.dumps(e.errors(), default=str)[:500])
    h = _hash(payload)
    stamp = monotonic()
    for expired in [scope for scope, entry in IDEM.items() if entry["expires_at"] <= stamp]:
        del IDEM[expired]
    sk = (token, request.method, request.url.path, key)
    rec = IDEM.get(sk)
    if rec:
        if rec["hash"] != h:
            raise ProblemError(422, "idempotency-key-reuse", "Idempotency key was already used with a different request body")
        if rec["state"] == "in_progress":
            raise ProblemError(409, "request-in-progress", "A request with this key is still being processed", headers={"Retry-After": "1"}, retryable=True)
        return JSONResponse(rec["body"], status_code=rec["status"], headers={**rec["headers"], "Idempotent-Replayed": "true"})
    IDEM[sk] = {"hash": h, "state": "in_progress", "expires_at": stamp + 86400}
    fault = request.headers.get("X-Mock-Fault")
    try:
        if fault == "503-once" and key not in FAULTED:
            FAULTED.add(key)
            raise ProblemError(503, "upstream-unavailable", "Upstream unavailable", retryable=True)
        status, body, headers = handler(payload)
    except ProblemError:
        IDEM.pop(sk, None)            # failures are not stored: the key can be retried
        raise
    IDEM[sk] = {"hash": h, "state": "done", "status": status, "body": deepcopy(body), "headers": headers, "expires_at": stamp + 86400}
    if fault == "commit-then-timeout" and key not in FAULTED:
        FAULTED.add(key)
        raise ProblemError(504, "upstream-timeout", "Gateway timeout after the write was committed. Retry with the same Idempotency-Key", retryable=True)
    return JSONResponse(body, status_code=status, headers=headers)


@app.post("/v1/cases", status_code=201)
async def create_case(request: Request, token: str = Depends(auth)):
    def h(p: CaseCreate):
        cust(p.customer_id)
        COUNTERS["case"] += 1
        cid = f"NXCASE-{COUNTERS['case']:06d}"
        CASES[cid] = {"case_id": cid, "customer_id": p.customer_id, "category": p.category, "priority": p.priority, "status": "OPEN", "summary": p.summary,
                      "related_application_id": p.related_application_id, "created_at": now(), "notes": [], "escalation": None, "_version": 1}
        return 201, _case_view(CASES[cid]), {"ETag": f'"{cid}-1"'}
    return await run_idempotent(request, token, CaseCreate, h)


def _case_view(c: dict) -> dict:
    return {k: v for k, v in c.items() if not k.startswith("_")}


def _case(case_id: str) -> dict:
    c = CASES.get(case_id)
    if not c:
        raise ProblemError(404, "not-found", "Case not found", case_id)
    return c


@app.get("/v1/cases/{caseId}")
def get_case(caseId: str, _: str = Depends(auth)):
    c = _case(caseId)
    return JSONResponse(_case_view(c), headers={"ETag": f'"{caseId}-{c["_version"]}"'})


@app.post("/v1/cases/{caseId}/notes", status_code=201)
async def add_note(caseId: str, request: Request, token: str = Depends(auth)):
    def h(p: NoteCreate):
        c = _case(caseId)
        COUNTERS["note"] += 1
        note = {"note_id": f"NXNOTE-{COUNTERS['note']:06d}", "case_id": caseId, "text": p.text, "created_at": now()}
        c["notes"].append(note); c["_version"] += 1
        return 201, note, {}
    return await run_idempotent(request, token, NoteCreate, h)


@app.post("/v1/cases/{caseId}/escalations", status_code=201)
async def escalate(caseId: str, request: Request, token: str = Depends(auth)):
    def h(p: EscalationCreate):
        c = _case(caseId)
        if c["status"] == "ESCALATED":
            raise ProblemError(409, "already-escalated", "Case is already escalated", caseId)
        COUNTERS["esc"] += 1
        esc = {"escalation_id": f"NXESC-{COUNTERS['esc']:06d}", "case_id": caseId, "status": "ESCALATED", "sla_hours": 4 if p.reason == "SUSPECTED_FRAUD" else 24}
        c["status"] = "ESCALATED"; c["escalation"] = {**esc, "reason": p.reason, "summary": p.summary, "preferred_contact": p.preferred_contact}; c["_version"] += 1
        return 201, esc, {}
    return await run_idempotent(request, token, EscalationCreate, h)


@app.post("/v1/service-requests", status_code=201)
async def service_request(request: Request, token: str = Depends(auth)):
    def h(p: ServiceRequestCreate):
        c = cust(p.customer_id)
        if p.request_type in ("OPT_IN_CIR_2026_07_PART_PREPAY", "INTEREST_CERTIFICATE"):
            loan = next((l for l in c["existing_loans"] if l["loan_account_id"] == p.loan_account_id), None)
            if loan is None:
                raise ProblemError(422, "validation-error", "loan_account_id is required and must belong to the customer")
            if p.request_type == "OPT_IN_CIR_2026_07_PART_PREPAY":
                if p.customer_id in OPTED_IN:
                    raise ProblemError(409, "already-opted-in", "This customer has already opted in")
                if loan["version_id"] != "NHL-2025-10":
                    raise ProblemError(422, "not-applicable", "Opt-in applies only to NexaHome loans sanctioned under POL-HL-V3 before 2026-07-01")
        COUNTERS["sr"] += 1
        sr_id = f"NXSR-{COUNTERS['sr']:06d}"
        sr = {"service_request_id": sr_id, "customer_id": p.customer_id, "request_type": p.request_type,
              "loan_account_id": p.loan_account_id, "status": "RECEIVED", "created_at": now()}
        SERVICE_REQUESTS[sr_id] = sr
        return 201, sr, {}
    return await run_idempotent(request, token, ServiceRequestCreate, h)


@app.post("/_mock/reset", include_in_schema=False)
def reset():
    CASES.clear(); SERVICE_REQUESTS.clear(); IDEM.clear(); FAULTED.clear()
    OPTED_IN.clear(); OPTED_IN.update(cid for cid, c in CUSTOMERS.items() if c["flags"]["opted_in_cir_2026_07_part_prepay_minimum"])
    for k in COUNTERS: COUNTERS[k] = 0
    return {"reset": True}
