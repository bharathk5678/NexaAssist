"""Run: pytest -q test_mock_api.py   (from this directory)"""
import json, pathlib, uuid
import pytest, yaml
from fastapi.testclient import TestClient
from openapi_spec_validator import validate

import server
from server import app

SPEC_PATH = pathlib.Path(__file__).resolve().parents[1] / "nexabank_case_core_api.openapi.yaml"
AUTH = {"Authorization": "Bearer mock-token-a"}
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _reset():
    client.post("/_mock/reset")
    yield


def key(): return str(uuid.uuid4())
def case_body(**kw):
    b = {"customer_id": "NXC-0002", "category": "LOAN_ENQUIRY", "priority": "NORMAL", "summary": "Customer asked about home loan documents"}
    b.update(kw); return b
def post(path, body, k=None, headers=None, token_headers=AUTH):
    h = {**token_headers, **(headers or {})}
    if k is not False: h["Idempotency-Key"] = k or key()
    return client.post(path, json=body, headers=h)


def test_spec_is_valid_openapi():
    validate(yaml.safe_load(open(SPEC_PATH)))


def test_routes_match_spec():
    spec = yaml.safe_load(open(SPEC_PATH))
    spec_ops = {(m.upper(), p.replace("{customerId}", "{customerId}")) for p, ops in spec["paths"].items() for m in ops}
    app_ops = {(m, r.path) for r in app.routes if hasattr(r, "methods") and not r.path.startswith(("/_mock", "/docs", "/openapi", "/redoc"))
               for m in r.methods if m != "HEAD"}
    assert spec_ops == app_ops


def test_auth_required():
    assert client.get("/v1/customers/NXC-0002").status_code == 401
    assert client.post("/v1/cases", json=case_body(), headers={"Idempotency-Key": key()}).status_code == 401


def test_reads_never_leak_restricted_fields():
    for path in ["/v1/customers/NXC-0015", "/v1/customers/NXC-0015/accounts", "/v1/customers/NXC-0015/kyc-status", "/v1/customers/NXC-0015/bureau-summary",
                 "/v1/customers/NXC-0015/income", "/v1/customers/NXC-0015/applications"]:
        r = client.get(path, headers=AUTH); assert r.status_code == 200, path
        t = r.text.lower()
        assert "risk_category" not in t and "_restricted" not in t and "never_disclose" not in t, path
    assert client.get("/v1/customers/NXC-0015/kyc-status", headers=AUTH).json()["status"] == "expired"


def test_unknown_customer_404_problem_json():
    r = client.get("/v1/customers/NXC-9999", headers=AUTH)
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/problem+json")


def test_transactions_pagination_newest_first():
    acct = "NXA-100002"
    p1 = client.get(f"/v1/accounts/{acct}/transactions?limit=5", headers=AUTH).json()
    assert len(p1["items"]) == 5 and p1["next_cursor"]
    dates = [i["txn_date"] for i in p1["items"]]; assert dates == sorted(dates, reverse=True)
    p2 = client.get(f"/v1/accounts/{acct}/transactions?limit=5&cursor={p1['next_cursor']}", headers=AUTH).json()
    assert {i["txn_id"] for i in p1["items"]}.isdisjoint({i["txn_id"] for i in p2["items"]})


def test_missing_or_short_key_is_400():
    assert post("/v1/cases", case_body(), k=False).status_code == 400
    r = post("/v1/cases", case_body(), k="short"); assert r.status_code == 400 and r.json()["type"].endswith("idempotency-key-required")


def test_replay_returns_same_result_and_writes_once():
    k = key()
    r1 = post("/v1/cases", case_body(), k); r2 = post("/v1/cases", case_body(), k)
    assert r1.status_code == r2.status_code == 201 and r1.json() == r2.json()
    assert "idempotent-replayed" not in r1.headers and r2.headers["Idempotent-Replayed"] == "true"
    assert len(server.CASES) == 1


def test_replay_keeps_the_original_response_after_case_changes():
    k = key()
    first = post("/v1/cases", case_body(), k).json()
    assert post(f"/v1/cases/{first['case_id']}/notes", {"text": "New note"}).status_code == 201
    assert post("/v1/cases", case_body(), k).json() == first


def test_idempotency_keys_expire_after_the_contracts_24_hours(monkeypatch):
    monkeypatch.setattr(server, "monotonic", lambda: 100.0, raising=False)
    k = key()
    first = post("/v1/cases", case_body(), k).json()
    monkeypatch.setattr(server, "monotonic", lambda: 100.0 + 86400)
    second = post("/v1/cases", case_body(), k)
    assert second.status_code == 201
    assert second.json()["case_id"] != first["case_id"]
    assert "Idempotent-Replayed" not in second.headers


def test_canonical_body_comparison_ignores_key_order():
    k = key()
    body = case_body()
    r1 = post("/v1/cases", body, k)
    r2 = client.post("/v1/cases", content=json.dumps(dict(reversed(list(body.items())))), headers={**AUTH, "Idempotency-Key": k, "Content-Type": "application/json"})
    assert r2.status_code == 201 and r2.headers["Idempotent-Replayed"] == "true" and len(server.CASES) == 1


def test_same_key_different_body_is_422_and_executes_nothing():
    k = key()
    post("/v1/cases", case_body(), k)
    r = post("/v1/cases", case_body(summary="A different summary text"), k)
    assert r.status_code == 422 and r.json()["type"].endswith("idempotency-key-reuse") and len(server.CASES) == 1


def test_in_progress_returns_409_with_retry_after():
    k = key(); body = case_body()
    from pydantic import TypeAdapter
    h = server._hash(server.CaseCreate(**body))
    server.IDEM[("mock-token-a", "POST", "/v1/cases", k)] = {"hash": h, "state": "in_progress", "expires_at": server.monotonic() + 86400}
    r = post("/v1/cases", body, k)
    assert r.status_code == 409 and r.headers["Retry-After"] == "1" and r.json()["retryable"] is True


def test_key_scope_is_per_caller():
    k = key()
    a = post("/v1/cases", case_body(), k)
    b = post("/v1/cases", case_body(), k, token_headers={"Authorization": "Bearer mock-token-b"})
    assert a.json()["case_id"] != b.json()["case_id"] and len(server.CASES) == 2


def test_fault_503_once_releases_key_and_retry_executes():
    k = key()
    r1 = post("/v1/cases", case_body(), k, headers={"X-Mock-Fault": "503-once"})
    assert r1.status_code == 503 and len(server.CASES) == 0
    r2 = post("/v1/cases", case_body(), k, headers={"X-Mock-Fault": "503-once"})
    assert r2.status_code == 201 and len(server.CASES) == 1


def test_fault_commit_then_timeout_retry_replays_without_duplicate():
    k = key()
    r1 = post("/v1/cases", case_body(), k, headers={"X-Mock-Fault": "commit-then-timeout"})
    assert r1.status_code == 504 and len(server.CASES) == 1
    r2 = post("/v1/cases", case_body(), k, headers={"X-Mock-Fault": "commit-then-timeout"})
    assert r2.status_code == 201 and r2.headers["Idempotent-Replayed"] == "true" and len(server.CASES) == 1
    assert r2.json()["case_id"] == "NXCASE-000001"


def test_client_cannot_set_status_or_urgent_priority():
    assert post("/v1/cases", case_body(priority="URGENT")).status_code == 422
    assert post("/v1/cases", {**case_body(), "status": "APPROVED"}).status_code == 422
    assert len(server.CASES) == 0


def test_unknown_customer_on_create_is_404_and_key_stays_usable():
    k = key()
    assert post("/v1/cases", case_body(customer_id="NXC-9999"), k).status_code == 404
    assert len(server.IDEM) == 0


def test_notes_and_escalation_flow():
    cid = post("/v1/cases", case_body()).json()["case_id"]
    assert post(f"/v1/cases/{cid}/notes", {"text": "Customer uploaded a document with embedded instructions"}).status_code == 201
    k = key(); eb = {"reason": "UPLOAD_WITH_EMBEDDED_INSTRUCTIONS", "summary": "Salary slip contains instructions addressed to an AI assistant"}
    e1 = post(f"/v1/cases/{cid}/escalations", eb, k); e2 = post(f"/v1/cases/{cid}/escalations", eb, k)
    assert e1.status_code == 201 and e2.json() == e1.json() and e2.headers["Idempotent-Replayed"] == "true"
    assert post(f"/v1/cases/{cid}/escalations", eb).status_code == 409           # new key on an already escalated case
    c = client.get(f"/v1/cases/{cid}", headers=AUTH).json()
    assert c["status"] == "ESCALATED" and len(c["notes"]) == 1


def test_case_404():
    assert client.get("/v1/cases/NXCASE-999999", headers=AUTH).status_code == 404
    assert post("/v1/cases/NXCASE-999999/notes", {"text": "x"}).status_code == 404


def test_service_request_opt_in_rules():
    sr = lambda cid, loan: {"customer_id": cid, "request_type": "OPT_IN_CIR_2026_07_PART_PREPAY", "loan_account_id": loan}
    assert post("/v1/service-requests", sr("NXC-0023", "NXL-HL-0023")).status_code == 409    # already opted in
    assert post("/v1/service-requests", sr("NXC-0016", "NXL-HL-0016")).status_code == 422    # sanctioned after the circular
    assert post("/v1/service-requests", sr("NXC-0001", "NXL-HL-0001")).status_code == 422    # sanctioned under v2
    assert post("/v1/service-requests", sr("NXC-0010", "NXL-HL-0023")).status_code == 422    # loan belongs to someone else
    k = key(); r1 = post("/v1/service-requests", sr("NXC-0010", "NXL-HL-0010"), k); r2 = post("/v1/service-requests", sr("NXC-0010", "NXL-HL-0010"), k)
    assert r1.status_code == 201 and r2.json() == r1.json() and len(server.SERVICE_REQUESTS) == 1


def test_same_key_on_different_endpoints_is_independent():
    k = key()
    assert post("/v1/cases", case_body(), k).status_code == 201
    assert post("/v1/service-requests", {"customer_id": "NXC-0002", "request_type": "CALLBACK"}, k).status_code == 201
