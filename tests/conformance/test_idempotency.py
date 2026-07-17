"""
Pack 5: Conformance — idempotency for POST message and approve.
Repeat same Idempotency-Key request returns same response and does not duplicate side effects.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import verify_api_key


@pytest.fixture
def client():
    store_module._store = None
    app.dependency_overrides[verify_api_key] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


def test_post_message_idempotency(client: TestClient):
    """POST /v1/chats/{id}/messages with same Idempotency-Key returns same 202 and single approval."""
    r = client.post("/v1/chats", json={"title": "Idem"})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    key = f"idem-msg-{uuid.uuid4().hex}"
    payload = {"content": "Hello idem"}
    r1 = client.post(
        f"/v1/chats/{chat_id}/messages",
        json=payload,
        headers={"Idempotency-Key": key},
    )
    assert r1.status_code == 202
    approval_id = r1.json().get("pending_approval_id")
    r2 = client.post(
        f"/v1/chats/{chat_id}/messages",
        json=payload,
        headers={"Idempotency-Key": key},
    )
    assert r2.status_code == 202
    assert r2.json().get("pending_approval_id") == approval_id
    r3 = client.get("/v1/approvals")
    assert len([a for a in r3.json()["approvals"] if a.get("status") == "pending"]) == 1


def test_approve_idempotency(client: TestClient):
    """POST /v1/approvals/{id}/approve with same Idempotency-Key returns same response."""
    r = client.post("/v1/chats", json={"title": "ApproveIdem"})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    r = client.post(f"/v1/chats/{chat_id}/messages", json={"content": "Hi"})
    assert r.status_code == 202
    approval_id = r.json()["pending_approval_id"]
    key = f"idem-approve-{uuid.uuid4().hex}"
    body = {"note": "ok"}
    r1 = client.post(f"/v1/approvals/{approval_id}/approve", json=body, headers={"Idempotency-Key": key})
    assert r1.status_code == 200
    r2 = client.post(f"/v1/approvals/{approval_id}/approve", json=body, headers={"Idempotency-Key": key})
    assert r2.status_code == 200
    assert r1.json().get("continued") == r2.json().get("continued")
