"""
Test plan: Gateway Tools (03_gateway_tools_execution)
- GET /v1/tools returns registry with schemas
- POST message with tool_invoke (read/none): executes, stores tool message, returns 200
- POST message with tool_invoke (write): returns 202; approve runs tool and returns 200
"""

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


def test_list_tools_returns_registry(client):
    r = client.get("/v1/tools")
    assert r.status_code == 200
    data = r.json()
    assert "tools" in data
    tools = data["tools"]
    assert isinstance(tools, list)
    if tools:
        t = tools[0]
        assert "name" in t
        assert "input_schema" in t or "description" in t


def test_tool_invoke_read_executes_and_stores(client):
    """Tool with effect none/read executes immediately and stores message."""
    r = client.post("/v1/chats", json={"title": "T"})
    chat_id = r.json()["chat_id"]
    r = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "", "tool_invoke": {"tool_name": "gateway.echo", "inputs": {"message": "hi"}}},
    )
    assert r.status_code == 200
    msg = r.json().get("message")
    assert msg
    assert msg.get("tool_name") == "gateway.echo"
    assert msg.get("tool_payload", {}).get("message") == "hi"
    assert "tool_result" in msg
    r = client.get(f"/v1/chats/{chat_id}/messages")
    msgs = r.json()["messages"]
    assert any(m.get("tool_name") == "gateway.echo" for m in msgs)


def test_tool_invoke_dry_run_returns_preview(client):
    r = client.post("/v1/chats", json={"title": "T"})
    chat_id = r.json()["chat_id"]
    r = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"tool_invoke": {"tool_name": "gateway.echo", "inputs": {"message": "hi"}, "dry_run": True}},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("dry_run", {}).get("dry_run") is True
    assert data["dry_run"].get("tool_name") == "gateway.echo"
    assert data["dry_run"].get("effect_class") == "none"


def test_tool_invoke_unknown_returns_404(client):
    r = client.post("/v1/chats", json={"title": "T"})
    chat_id = r.json()["chat_id"]
    r = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"tool_invoke": {"tool_name": "nonexistent.tool", "inputs": {}}},
    )
    assert r.status_code == 404
