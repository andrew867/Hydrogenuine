"""
Pack3 Phase 3: Tool safety e2e — SSRF blocked before execution; policy returns structured denial.
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


def test_tool_invoke_ssrf_blocked_returns_403(client_sqlite):
    """Tool invoke with base_url=127.0.0.1 is denied before execution; 403 with structured body."""
    r = client_sqlite.post("/v1/chats", json={})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    r = client_sqlite.post(
        f"/v1/chats/{chat_id}/messages",
        json={
            "tool_invoke": {
                "tool_name": "moltbook.post_or_reply",
                "inputs": {"base_url": "http://127.0.0.1/", "content": "x"},
            },
        },
    )
    assert r.status_code == 403
    data = r.json()
    assert "detail" in data
    detail = data["detail"]
    if isinstance(detail, dict):
        assert detail.get("code") == "ssrf_blocked"
        assert "reason" in detail or "reason" in str(detail)
    else:
        assert "ssrf" in str(detail).lower() or "blocked" in str(detail).lower()


def test_tool_invoke_private_ip_blocked(client_sqlite):
    """base_url with 192.168.x is blocked."""
    r = client_sqlite.post("/v1/chats", json={})
    chat_id = r.json()["chat_id"]
    r = client_sqlite.post(
        f"/v1/chats/{chat_id}/messages",
        json={
            "tool_invoke": {
                "tool_name": "moltbook.post_or_reply",
                "inputs": {"base_url": "http://192.168.1.1/api", "content": "y"},
            },
        },
    )
    assert r.status_code == 403


def test_tool_invoke_public_url_allowed_creates_approval(client_sqlite):
    """Tool invoke with public base_url passes policy and creates approval (202)."""
    r = client_sqlite.post("/v1/chats", json={})
    chat_id = r.json()["chat_id"]
    r = client_sqlite.post(
        f"/v1/chats/{chat_id}/messages",
        json={
            "tool_invoke": {
                "tool_name": "moltbook.post_or_reply",
                "inputs": {"base_url": "https://api.example.com/v1", "content": "hello"},
            },
        },
    )
    assert r.status_code == 202
    assert "pending_approval_id" in r.json()
