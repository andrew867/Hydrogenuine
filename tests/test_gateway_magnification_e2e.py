"""
Pack2-03: Magnification e2e. Real gateway, real rules, tool-invoke approval risk from magnification.
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


def test_magnify_api_returns_report(client_sqlite):
    """POST /v1/alignment/magnify with planned_action returns MagnificationReport (risk_score, required_controls)."""
    r = client_sqlite.post(
        "/v1/alignment/magnify",
        json={
            "planned_action": {"tool_name": "moltbook.post_or_reply", "inputs": {"base_url": "http://x", "content": "y"}},
            "context": {},
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "risk_score" in data
    assert data["risk_score"] == 75
    assert data.get("required_controls", {}).get("step_up_auth") == "strong"
    assert data.get("required_controls", {}).get("approval") is True
    assert "reasons" in data
    assert "suggested_tests" in data


def test_magnify_gateway_echo_low_risk(client_sqlite):
    """POST /v1/alignment/magnify for gateway.echo returns risk_score 0, no approval required."""
    r = client_sqlite.post(
        "/v1/alignment/magnify",
        json={"planned_action": {"tool_name": "gateway.echo", "inputs": {"message": "hi"}}},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["risk_score"] == 0
    assert data["required_controls"]["step_up_auth"] == "none"
    assert data["required_controls"]["approval"] is False


def test_tool_invoke_high_risk_approval_created(client_sqlite):
    """Requesting moltbook.post_or_reply creates pending approval with risk=high (magnification wired)."""
    r = client_sqlite.post("/v1/chats", json={})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]

    r = client_sqlite.post(
        f"/v1/chats/{chat_id}/messages",
        json={
            "tool_invoke": {
                "tool_name": "moltbook.post_or_reply",
                "inputs": {"base_url": "https://api.example.com/v1", "content": "e2e"},
            },
        },
    )
    assert r.status_code == 202  # Pack3: public URL passes SSRF guard; high-risk still creates approval
    data = r.json()
    approval_id = data.get("pending_approval_id")
    assert approval_id

    r = client_sqlite.get("/v1/approvals")
    assert r.status_code == 200
    approvals = r.json().get("approvals") or []
    found = next((a for a in approvals if a.get("id") == approval_id), None)
    assert found is not None
    assert found.get("risk") == "high"
    assert found.get("kind") == "tool_invoke"


def test_tool_invoke_medium_risk_approval(client_sqlite):
    """Requesting gateway.echo (write in registry) would get medium if write; echo is none so no approval. Use a tool that is write but lower magnification score."""
    r = client_sqlite.post("/v1/chats", json={})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    r = client_sqlite.post(
        f"/v1/chats/{chat_id}/messages",
        json={
            "tool_invoke": {
                "tool_name": "moltbook.submit_verification",
                "inputs": {"validation_endpoint": "http://x/verify", "verification_code": "c", "answer": "5"},
            },
        },
    )
    assert r.status_code == 202
    data = r.json()
    approval_id = data.get("pending_approval_id")
    assert approval_id
    r = client_sqlite.get("/v1/approvals")
    approvals = r.json().get("approvals") or []
    found = next((a for a in approvals if a.get("id") == approval_id), None)
    assert found is not None
    assert found.get("risk") == "medium"
