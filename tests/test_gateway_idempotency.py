"""
Pack3 Phase 2: Idempotency and tool-effect dedupe tests.

- POST message twice with same Idempotency-Key + same body -> identical response
- Same key + different body -> 409
- Approve twice with same key -> both succeed, no double-resolve
- Tool executed twice with same effects (same chat, tool, inputs) -> second returns cached result
"""

import os
import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import verify_api_key


@pytest.fixture
def client_sqlite(tmp_path):
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


def test_post_message_same_idempotency_key_same_body_returns_same_response(client_sqlite):
    """POST message twice with same Idempotency-Key and same body yields same message_id."""
    r = client_sqlite.post("/v1/chats", json={})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    body = {"content": "Hello idem"}
    headers = {"Idempotency-Key": "idem-msg-001"}
    r1 = client_sqlite.post(f"/v1/chats/{chat_id}/messages", json=body, headers=headers)
    assert r1.status_code == 202
    data1 = r1.json()
    r2 = client_sqlite.post(f"/v1/chats/{chat_id}/messages", json=body, headers=headers)
    assert r2.status_code == 202
    data2 = r2.json()
    assert data1.get("pending_approval_id") == data2.get("pending_approval_id")
    assert data1.get("message") == data2.get("message")


def test_post_message_same_idempotency_key_different_body_returns_409(client_sqlite):
    """Same Idempotency-Key with different body -> 409 Conflict."""
    r = client_sqlite.post("/v1/chats", json={})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    headers = {"Idempotency-Key": "idem-msg-002"}
    client_sqlite.post(f"/v1/chats/{chat_id}/messages", json={"content": "First"}, headers=headers)
    r2 = client_sqlite.post(f"/v1/chats/{chat_id}/messages", json={"content": "Other"}, headers=headers)
    assert r2.status_code == 409
    assert "conflict" in r2.json().get("detail", "").lower() or "match" in r2.json().get("detail", "").lower()


def test_approve_twice_same_idempotency_key_both_succeed(client_sqlite):
    """Approve twice with same Idempotency-Key -> both return 200, approval not double-resolved."""
    r = client_sqlite.post("/v1/chats", json={})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    client_sqlite.post(f"/v1/chats/{chat_id}/messages", json={"content": "Hi"})
    r = client_sqlite.get("/v1/approvals")
    assert r.status_code == 200
    approval_id = r.json()["approvals"][0]["id"]
    headers = {"Idempotency-Key": "idem-approve-001"}
    r1 = client_sqlite.post(f"/v1/approvals/{approval_id}/approve", json={"note": "ok"}, headers=headers)
    assert r1.status_code == 200
    r2 = client_sqlite.post(f"/v1/approvals/{approval_id}/approve", json={"note": "ok"}, headers=headers)
    assert r2.status_code == 200
    assert r1.json().get("continued") == r2.json().get("continued")


def test_tool_same_effects_hash_returns_cached_result(client_sqlite):
    """Tool invoked twice with same tool_name + inputs + chat_id -> second response uses cached result."""
    r = client_sqlite.post("/v1/chats", json={})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    payload = {"tool_name": "gateway.echo", "inputs": {"message": "cached-test"}}
    r1 = client_sqlite.post(f"/v1/chats/{chat_id}/messages", json={"tool_invoke": payload})
    assert r1.status_code == 200
    m1 = r1.json().get("message") or {}
    r2 = client_sqlite.post(f"/v1/chats/{chat_id}/messages", json={"tool_invoke": payload})
    assert r2.status_code == 200
    m2 = r2.json().get("message") or {}
    assert m1.get("tool_result") is not None
    assert m2.get("tool_result") is not None
    assert m1.get("tool_result") == m2.get("tool_result")
