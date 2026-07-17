"""
Test plan: Chat Approvals (02_chat_approvals_wiring)
- Integration: trigger approval-required (first message), see pending, approve, turn continues
- Deny: no side effects, 204
- approval_get, approval.created / approval.resolved events and audit
"""

import os
from unittest.mock import patch

import pytest
import pyotp
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import verify_api_key
from hg_gateway.store import get_store


@pytest.fixture
def client(tmp_path):
    store_module._store = None
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    app.dependency_overrides[verify_api_key] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        os.environ.pop("HG_GATEWAY_DB_PATH", None)


def test_first_message_returns_202_pending_approval(client):
    """First user message in a chat triggers approval; response is 202 with pending_approval_id."""
    r = client.post("/v1/chats", json={"title": "Test"})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    r = client.post(f"/v1/chats/{chat_id}/messages", json={"content": "Hello"})
    assert r.status_code == 202
    data = r.json()
    assert "pending_approval_id" in data
    assert data["message"] == "Approval required before assistant reply."
    approval_id = data["pending_approval_id"]
    r = client.get("/v1/approvals")
    assert r.status_code == 200
    approvals = r.json()["approvals"]
    assert len(approvals) == 1
    assert approvals[0]["id"] == approval_id
    assert approvals[0]["status"] == "pending"


def test_approve_continues_turn_returns_200(client):
    """After first message 202, approving runs the turn and returns 200 with message."""
    r = client.post("/v1/chats", json={"title": "Test"})
    chat_id = r.json()["chat_id"]
    r = client.post(f"/v1/chats/{chat_id}/messages", json={"content": "Hi"})
    assert r.status_code == 202
    approval_id = r.json()["pending_approval_id"]
    r = client.post(f"/v1/approvals/{approval_id}/approve", json={"note": "ok"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("continued") is True
    assert "message" in data
    assert data["message"]["role"] == "assistant"
    assert "content" in data["message"]
    r = client.get(f"/v1/chats/{chat_id}/messages")
    msgs = r.json()["messages"]
    assert len(msgs) >= 2
    assert msgs[0]["role"] == "user"
    assert msgs[-1]["role"] == "assistant"


def test_deny_returns_204_no_turn(client):
    """Denying approval returns 204; no assistant message added."""
    r = client.post("/v1/chats", json={"title": "Test"})
    chat_id = r.json()["chat_id"]
    r = client.post(f"/v1/chats/{chat_id}/messages", json={"content": "Hi"})
    assert r.status_code == 202
    approval_id = r.json()["pending_approval_id"]
    r = client.post(f"/v1/approvals/{approval_id}/deny", json={"note": "nope"})
    assert r.status_code == 204
    r = client.get(f"/v1/chats/{chat_id}/messages")
    msgs = r.json()["messages"]
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"


def test_second_message_no_approval_runs_turn(client):
    """Second user message (after first was approved) does not require approval; turn runs."""
    r = client.post("/v1/chats", json={"title": "Test"})
    chat_id = r.json()["chat_id"]
    r = client.post(f"/v1/chats/{chat_id}/messages", json={"content": "First"})
    assert r.status_code == 202
    approval_id = r.json()["pending_approval_id"]
    client.post(f"/v1/approvals/{approval_id}/approve")
    r = client.post(f"/v1/chats/{chat_id}/messages", json={"content": "Second"})
    assert r.status_code == 200
    assert "message" in r.json()
    assert r.json()["message"]["role"] == "assistant"


def test_auth_required_without_key(tmp_path):
    from hg_gateway.main import app
    store_module._store = None
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    try:
        client = TestClient(app)
        r = client.get("/v1/chats")
        assert r.status_code == 401
    finally:
        os.environ.pop("HG_GATEWAY_DB_PATH", None)


def test_approval_get_store(client):
    """Store.approval_get returns approval with payload and chat_id. Pack3: tenant_id required."""
    from hg_gateway.store import get_store
    store = get_store()
    tenant_id = "default"
    cid = store.chat_create(tenant_id, title="X")
    aid = store.approval_add(tenant_id, "test", "T", "S", "low", "u", {"type": "chat_turn", "chat_id": cid}, chat_id=cid)
    a = store.approval_get(tenant_id, aid)
    assert a is not None
    assert a["id"] == aid
    assert a["status"] == "pending"
    assert a["payload"].get("type") == "chat_turn"
    assert a["chat_id"] == cid


def test_list_approvals_pagination_limit_offset_total(client):
    """GET /v1/approvals with limit and offset returns approvals and total."""
    store = get_store()
    tenant_id = "default"
    for i in range(7):
        store.approval_add(
            tenant_id, "other", f"Title {i}", "Summary", "low", "u", {"x": i}
        )
    r = client.get("/v1/approvals", params={"status": "all", "limit": 5, "offset": 0})
    assert r.status_code == 200
    data = r.json()
    assert "approvals" in data
    assert "total" in data
    assert len(data["approvals"]) <= 5
    assert data["total"] == 7
    r2 = client.get("/v1/approvals", params={"status": "all", "limit": 5, "offset": 5})
    assert r2.status_code == 200
    data2 = r2.json()
    assert len(data2["approvals"]) == 2
    assert data2["total"] == 7


def test_social_write_approve_executes_and_records_artifact(client, tmp_path):
    draft_path = tmp_path / "social-approval.json"
    draft_path.write_text("{}", encoding="utf-8")
    store = get_store()
    approval_id = store.approval_add(
        "default",
        kind="social_write",
        title="Approve social post",
        summary="Pending post",
        risk="high",
        requested_by="automation-fourclaw-auto-post",
        payload={
            "type": "social_write_review",
            "task_name": "fourclaw-auto-post",
            "platform": "fourclaw",
            "mode": "post",
            "draft_title": "Hello",
            "draft_content": "Body",
            "draft_artifact": str(draft_path),
        },
    )
    with patch(
        "hg_core.task_graph.native_task_tools.execute_social_write_approval",
        return_value={
            "ok": True,
            "outputs": {
                "thread_id": "thread-123",
                "thread_url": "https://example.invalid/t/thread-123",
                "result": {
                    "status": "completed",
                    "mode": "live",
                    "platform": "fourclaw",
                    "thread_id": "thread-123",
                    "thread_url": "https://example.invalid/t/thread-123",
                    "external_calls": 1,
                },
            },
            "returncode": 0,
            "external_calls": 1,
        },
    ):
        secret = client.post("/v1/auth/stepup/enroll", json={"user_id": "default", "secret": "JBSWY3DPEHPK3PXP"}).json()["secret"]
        challenge = client.post("/v1/auth/stepup/challenge", json={"user_id": "default"})
        token = client.post(
            "/v1/auth/stepup/verify",
            json={"challenge_id": challenge.json()["challenge_id"], "code": pyotp.TOTP(secret).now()},
        ).json()["stepup_token"]
        response = client.post(
            f"/v1/approvals/{approval_id}/approve",
            json={"note": "ship it"},
            headers={"X-HG-Stepup": token},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["continued"] is True
    assert data["execution"]["thread_id"] == "thread-123"
    artifact = draft_path.read_text(encoding="utf-8")
    assert '"decision": "approved"' in artifact
    assert '"thread_id": "thread-123"' in artifact


def test_social_write_deny_records_cancelled_artifact(client, tmp_path):
    draft_path = tmp_path / "social-denied.json"
    draft_path.write_text("{}", encoding="utf-8")
    store = get_store()
    approval_id = store.approval_add(
        "default",
        kind="social_write",
        title="Approve social reply",
        summary="Pending reply",
        risk="high",
        requested_by="automation-fourclaw-engage",
        payload={
            "type": "social_write_review",
            "task_name": "fourclaw-engage",
            "platform": "fourclaw",
            "mode": "reply",
            "thread_id": "thread-456",
            "draft_title": "Reply",
            "draft_content": "Body",
            "draft_artifact": str(draft_path),
        },
    )
    response = client.post(f"/v1/approvals/{approval_id}/deny", json={"note": "not now"})
    assert response.status_code == 204
    artifact = draft_path.read_text(encoding="utf-8")
    assert '"decision": "denied"' in artifact
    assert '"status": "cancelled"' in artifact
