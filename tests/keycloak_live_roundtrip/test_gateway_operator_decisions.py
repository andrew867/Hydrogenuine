"""Gateway operator-decision binding (mission cases 1-19) — fixture-JWKS + TestClient."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from tests.keycloak_live_roundtrip.conftest import CLIENT_ID, ISSUER, mint


@pytest.fixture()
def client(monkeypatch, tmp_path, jwks_file):
    monkeypatch.setenv("HG_GATEWAY_STORE", "memory")
    monkeypatch.setenv("HG_OPERATOR_AUTH_MODE", "keycloak")
    monkeypatch.setenv("HG_OIDC_JWKS_FILE", jwks_file)
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:8180")
    monkeypatch.setenv("KEYCLOAK_REALM", "hg")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", CLIENT_ID)
    monkeypatch.setenv("HG_OPERATOR_DECISION_DIR", str(tmp_path / "decisions"))
    from hg_gateway.main import app
    return TestClient(app), tmp_path / "decisions"


def _bearer(tok):
    return {"Authorization": f"Bearer {tok}"}


def test_valid_token_approval_bound_to_keycloak_subject(client, rsa_keys):
    c, sink = client
    sub = "11111111-2222-3333-4444-555555555555"
    tok = mint(rsa_keys, roles=("operator",), sub=sub)
    r = c.post("/v1/operator/approvals/appr-1/approve",
               headers=_bearer(tok), json={"action_class": "promotion"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["decided_by_subject"] == sub
    assert body["production_operator_auth"] is True
    assert body["demo_local_signing"] is False
    # receipt persisted, no raw token
    rec = json.loads((sink / f"{body['receipt_id']}.json").read_text(encoding="utf-8"))
    assert rec["operator_identity"]["subject"] == sub
    assert "eyJ" not in json.dumps(rec)


def test_invalid_signature_rejected(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, wrong_key=True)
    r = c.post("/v1/operator/approvals/a/approve", headers=_bearer(tok),
               json={"action_class": "promotion"})
    assert r.status_code == 401


def test_expired_token_rejected(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, exp_delta=-10)
    r = c.post("/v1/operator/approvals/a/approve", headers=_bearer(tok),
               json={"action_class": "promotion"})
    assert r.status_code == 401


def test_wrong_issuer_rejected(client, rsa_keys, monkeypatch):
    c, _ = client
    monkeypatch.setenv("KEYCLOAK_URL", "http://localhost:9999")  # issuer mismatch
    tok = mint(rsa_keys)
    r = c.post("/v1/operator/approvals/a/approve", headers=_bearer(tok),
               json={"action_class": "promotion"})
    assert r.status_code == 401


def test_missing_role_rejected(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("viewer",))
    r = c.post("/v1/operator/approvals/a/approve", headers=_bearer(tok),
               json={"action_class": "promotion"})
    assert r.status_code in (401, 403)


def test_service_role_rejected_for_approval(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("service", "operator"))
    r = c.post("/v1/operator/approvals/a/approve", headers=_bearer(tok),
               json={"action_class": "promotion"})
    assert r.status_code == 403


def test_unauthenticated_operator_endpoint_rejected(client):
    c, sink = client
    r = c.post("/v1/operator/approvals/a/approve", json={"action_class": "promotion"})
    assert r.status_code == 401
    # fail closed: no decision record written
    assert not (sink.exists() and any(sink.iterdir()))


def test_session_hash_and_no_raw_token_in_me(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator",))
    r = c.get("/v1/operator/me", headers=_bearer(tok))
    assert r.status_code == 200
    body = r.json()
    assert body["session_id_hash"].startswith("sha256:")
    assert "eyJ" not in json.dumps(body)
    assert tok not in json.dumps(body)


def test_denial_bound_no_stepup_by_default(client, rsa_keys):
    c, sink = client
    sub = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    tok = mint(rsa_keys, roles=("operator",), sub=sub)
    r = c.post("/v1/operator/approvals/appr-9/deny",
               headers=_bearer(tok), json={"action_class": "external_effect"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["decision"] == "deny"
    assert body["decided_by_subject"] == sub
    assert body["step_up_required"] is False


def test_high_risk_without_stepup_held(client, rsa_keys):
    c, sink = client
    tok = mint(rsa_keys, roles=("operator", "hg.memory_admin", "hg.high_risk_approver"))
    r = c.post("/v1/operator/approvals/hr-1/approve",
               headers=_bearer(tok), json={"action_class": "memory_mutation"})
    assert r.status_code == 403
    detail = r.json()["detail"]
    assert detail["code"] == "operator_decision_held"
    assert detail["step_up_required"] is True
    # a refusal receipt was still written (evidence), but no approval took effect
    assert (sink / f"{detail['receipt_id']}.json").exists()


def test_breakglass_without_reason_held(client, rsa_keys):
    c, _ = client
    tok = mint(rsa_keys, roles=("operator", "hg.breakglass"), amr=("pwd", "otp"))
    r = c.post("/v1/operator/approvals/bg-1/approve",
               headers=_bearer(tok),
               json={"action_class": "breakglass", "breakglass_reason": ""})
    assert r.status_code == 403
    assert r.json()["detail"]["reason"] in ("breakglass_reason_required", "step_up_missing")


def test_fixture_amr_token_passes_high_risk(client, rsa_keys):
    c, sink = client
    # test-only fixture token carrying amr=otp evidence proves the PASS path
    tok = mint(rsa_keys, roles=("operator", "hg.memory_admin", "hg.high_risk_approver"),
               amr=("pwd", "otp"))
    r = c.post("/v1/operator/approvals/hr-2/approve",
               headers=_bearer(tok), json={"action_class": "memory_mutation"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["step_up_required"] is True and body["step_up_satisfied"] is True


def test_demo_local_mode_cannot_claim_production(client, rsa_keys, monkeypatch):
    c, sink = client
    monkeypatch.setenv("HG_OPERATOR_AUTH_MODE", "demo_local")
    r = c.post("/v1/operator/approvals/dl-1/approve", json={"action_class": "promotion"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["production_operator_auth"] is False
    assert body["demo_local_signing"] is True


def test_decision_receipt_chain_validates(client, rsa_keys):
    c, sink = client
    tok = mint(rsa_keys, roles=("operator",), sub="chain-sub-0001-aaaa-bbbb-cccc")
    for i in range(2):
        r = c.post(f"/v1/operator/approvals/chain-{i}/approve",
                   headers=_bearer(tok), json={"action_class": "promotion"})
        assert r.status_code == 200
    from hg_operator_auth.receipts import verify_receipt_chain
    lines = [json.loads(l) for l in
             (sink / "decision_chain.jsonl").read_text(encoding="utf-8").splitlines()
             if l.strip()]
    assert verify_receipt_chain(lines)["ok"]
