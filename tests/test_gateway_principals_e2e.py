"""
Pack2-08: Principals and approval routing e2e. Real SQLite store; no mocks.
"""

import os
import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import verify_api_key


@pytest.fixture
def client_sqlite(tmp_path):
    """Client with SQLite store and principals in same DB."""
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


def test_principals_api_crud(client_sqlite):
    """POST principal, GET list, GET by id, PATCH availability — real data."""
    r = client_sqlite.post("/v1/principals", json={"id": "op1", "type": "user", "label": "Operator 1", "status": "online"})
    assert r.status_code == 200
    assert r.json()["id"] == "op1"
    assert r.json()["status"] == "online"
    r = client_sqlite.post("/v1/principals", json={
        "id": "op2", "type": "user", "label": "Operator 2", "status": "offline",
        "escalation_chain": ["op1", "op2"],
    })
    assert r.status_code == 200
    r = client_sqlite.get("/v1/principals")
    assert r.status_code == 200
    principals = r.json()["principals"]
    assert len(principals) == 2
    r = client_sqlite.get("/v1/principals/op1")
    assert r.status_code == 200
    assert r.json()["label"] == "Operator 1"
    r = client_sqlite.patch("/v1/principals/op2/availability", json={"status": "away"})
    assert r.status_code == 200
    assert r.json()["status"] == "away"
    r = client_sqlite.get("/v1/principals/nonexistent")
    assert r.status_code == 404


def test_approval_routing_assigns_principal(client_sqlite):
    """Create principals with escalation chain; first message triggers approval; approval has assignedPrincipalId."""
    # Principal op1 online, op2 offline; chain [op1, op2] -> op1 assigned
    client_sqlite.post("/v1/principals", json={
        "id": "op1", "type": "user", "label": "Primary", "status": "online",
        "escalation_chain": ["op1", "op2"],
    })
    client_sqlite.post("/v1/principals", json={"id": "op2", "type": "user", "label": "Secondary", "status": "offline"})
    r = client_sqlite.post("/v1/chats", json={"title": "Approval test"})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    r = client_sqlite.post(f"/v1/chats/{chat_id}/messages", json={"content": "Hello"})
    assert r.status_code == 202
    approval_id = r.json()["pending_approval_id"]
    r = client_sqlite.get("/v1/approvals")
    assert r.status_code == 200
    approvals = r.json()["approvals"]
    assert len(approvals) == 1
    assert approvals[0]["id"] == approval_id
    assert approvals[0].get("assignedPrincipalId") == "op1"
