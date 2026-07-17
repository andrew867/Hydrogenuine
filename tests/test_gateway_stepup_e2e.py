"""
Pack2-06: Step-up auth e2e. Real TOTP, real DB, no mocks.
Enroll → challenge → verify → stepup_token; high-risk approve with/without token.
"""

import os
import pytest
import pyotp
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.store import get_store
from hg_gateway.auth import verify_api_key


@pytest.fixture
def client_sqlite(tmp_path):
    """Client with SQLite store and step-up tables in same DB."""
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    store_module._store = None
    app.dependency_overrides[verify_api_key] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        os.environ.pop("HG_GATEWAY_STORE", None)
        os.environ.pop("HG_GATEWAY_DB_PATH", None)


def test_stepup_enroll_challenge_verify(client_sqlite):
    """Enroll default user, create challenge, verify with real TOTP code → stepup_token."""
    r = client_sqlite.post("/v1/auth/stepup/enroll", json={"user_id": "default"})
    assert r.status_code == 200
    data = r.json()
    assert "secret" in data
    assert "provisioning_uri" in data
    secret = data["secret"]

    r = client_sqlite.post("/v1/auth/stepup/challenge", json={})
    assert r.status_code == 200
    ch = r.json()
    assert ch.get("method") == "totp"
    challenge_id = ch["challenge_id"]

    code = pyotp.TOTP(secret).now()
    r = client_sqlite.post("/v1/auth/stepup/verify", json={"challenge_id": challenge_id, "code": code})
    assert r.status_code == 200
    assert "stepup_token" in r.json()


def test_stepup_challenge_404_when_not_enrolled(client_sqlite):
    """Challenge for non-enrolled user returns 404."""
    r = client_sqlite.post("/v1/auth/stepup/challenge", json={"user_id": "nobody"})
    assert r.status_code == 404


def test_stepup_verify_invalid_code(client_sqlite):
    """Verify with wrong code returns 401."""
    client_sqlite.post("/v1/auth/stepup/enroll", json={"user_id": "default"})
    r = client_sqlite.post("/v1/auth/stepup/challenge", json={})
    assert r.status_code == 200
    challenge_id = r.json()["challenge_id"]
    r = client_sqlite.post("/v1/auth/stepup/verify", json={"challenge_id": challenge_id, "code": "000000"})
    assert r.status_code == 401


def test_high_risk_approve_without_stepup_returns_403(client_sqlite):
    """High-risk approval without X-HG-Stepup returns 403 stepup_required."""
    store = get_store()
    tenant_id = "default"
    approval_id = store.approval_add(
        tenant_id,
        kind="chat_turn",
        title="High-risk test",
        summary="Test",
        risk="high",
        requested_by="test",
        payload={"type": "chat_turn", "chat_id": "c1", "messages_for_llm": []},
        chat_id="c1",
    )
    r = client_sqlite.post(f"/v1/approvals/{approval_id}/approve", json={})
    assert r.status_code == 403
    assert r.json().get("code") == "stepup_required"


def test_high_risk_approve_with_stepup_succeeds(client_sqlite):
    """Enroll → challenge → verify → approve high-risk with X-HG-Stepup → 200."""
    r = client_sqlite.post("/v1/auth/stepup/enroll", json={"user_id": "default"})
    assert r.status_code == 200
    secret = r.json()["secret"]
    r = client_sqlite.post("/v1/auth/stepup/challenge", json={})
    assert r.status_code == 200
    challenge_id = r.json()["challenge_id"]
    code = pyotp.TOTP(secret).now()
    r = client_sqlite.post("/v1/auth/stepup/verify", json={"challenge_id": challenge_id, "code": code})
    assert r.status_code == 200
    stepup_token = r.json()["stepup_token"]

    store = get_store()
    tenant_id = "default"
    approval_id = store.approval_add(
        tenant_id,
        kind="chat_turn",
        title="High-risk with step-up",
        summary="Test",
        risk="high",
        requested_by="test",
        payload={"type": "chat_turn", "chat_id": "c1", "messages_for_llm": []},
        chat_id="c1",
    )
    r = client_sqlite.post(
        f"/v1/approvals/{approval_id}/approve",
        json={},
        headers={"X-HG-Stepup": stepup_token},
    )
    assert r.status_code == 200


def test_low_risk_approve_without_stepup_succeeds(client_sqlite):
    """Low-risk approval does not require step-up; approve without token succeeds."""
    store = get_store()
    tenant_id = "default"
    approval_id = store.approval_add(
        tenant_id,
        kind="tool_invoke",
        title="Low-risk",
        summary="Test",
        risk="low",
        requested_by="test",
        payload={"type": "tool_invoke", "tool_name": "noop", "inputs": {}},
        chat_id="c1",
    )
    r = client_sqlite.post(f"/v1/approvals/{approval_id}/approve", json={})
    assert r.status_code == 200
