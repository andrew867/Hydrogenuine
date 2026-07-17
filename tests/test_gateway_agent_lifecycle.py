"""
Tests for Pack 10 agent lifecycle: list agents includes state; pause/resume/quarantine/release;
run_turn and tool execution blocked when agent paused or quarantined (423).
"""

import os
import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import verify_api_key, verify_admin_key, require_admin


@pytest.fixture
def client(tmp_path):
    store_module._store = None
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    app.dependency_overrides[verify_api_key] = lambda: None
    # The agent-lifecycle routes (pause/resume/quarantine/release) depend on
    # require_admin, not the legacy verify_admin_key. Override the dependency the
    # routes actually declare; keep verify_admin_key for any legacy route still on
    # it. Test-only override of the admin gate — production auth is unchanged and is
    # exercised directly by test_lifecycle_admin_auth_contract below.
    app.dependency_overrides[verify_admin_key] = lambda: None
    app.dependency_overrides[require_admin] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        app.dependency_overrides.pop(verify_admin_key, None)
        app.dependency_overrides.pop(require_admin, None)
        os.environ.pop("HG_GATEWAY_DB_PATH", None)


@pytest.fixture
def chat_with_agent(client):
    """Create a chat and trigger one turn so agent exists, then return chat_id."""
    r = client.post("/v1/chats", json={"title": "Lifecycle test"})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    r = client.post(f"/v1/chats/{chat_id}/messages", json={"content": "Hello"})
    if r.status_code == 202:
        approval_id = r.json().get("pending_approval_id")
        if approval_id:
            client.post(f"/v1/approvals/{approval_id}/approve", json={"note": "ok"})
    r = client.get(f"/v1/chats/{chat_id}/agents")
    assert r.status_code == 200
    agents = r.json().get("agents", [])
    if not agents:
        store = store_module.get_store()
        store.agent_upsert("default", chat_id, "primary", "Primary", "idle")
    return chat_id


def test_list_agents_includes_lifecycle_state(client, chat_with_agent):
    """GET /chats/{id}/agents returns lifecycle_state, state_reason, state_updated_at, state_updated_by."""
    chat_id = chat_with_agent
    r = client.get(f"/v1/chats/{chat_id}/agents")
    assert r.status_code == 200
    agents = r.json()["agents"]
    assert len(agents) >= 1
    primary = next((a for a in agents if a.get("agent_id") == "primary"), None)
    assert primary is not None
    assert "lifecycle_state" in primary
    assert primary.get("lifecycle_state") in ("active", "paused", "quarantined")
    assert "state_reason" in primary
    assert "state_updated_at" in primary
    assert "state_updated_by" in primary


def test_pause_requires_admin_key(client, chat_with_agent):
    """POST pause without admin key returns 403 (or 503 if admin key not configured)."""
    chat_id = chat_with_agent
    # Remove the test-only admin bypass so the real require_admin dependency runs.
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(verify_admin_key, None)
    prev = os.environ.get("HG_GATEWAY_ADMIN_KEY")
    try:
        os.environ["HG_GATEWAY_ADMIN_KEY"] = "required-key"
        r = client.post(
            f"/v1/chats/{chat_id}/agents/primary/pause",
            json={"reason": "test"},
            headers={},
        )
        assert r.status_code == 403
        # And a correct admin key is accepted by the same route.
        r_ok = client.post(
            f"/v1/chats/{chat_id}/agents/primary/pause",
            json={"reason": "test"},
            headers={"X-Admin-Key": "required-key"},
        )
        assert r_ok.status_code == 200
    finally:
        if prev is not None:
            os.environ["HG_GATEWAY_ADMIN_KEY"] = prev
        else:
            os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)
        app.dependency_overrides[verify_admin_key] = lambda: None
        app.dependency_overrides[require_admin] = lambda: None


def test_pause_resume_roundtrip(client, chat_with_agent):
    """POST pause then resume; list shows state; 200 and payload with lifecycle_state."""
    chat_id = chat_with_agent
    r = client.post(
        f"/v1/chats/{chat_id}/agents/primary/pause",
        json={"reason": "test pause", "updated_by": "operator"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("lifecycle_state") == "paused"
    assert data.get("state_reason") == "test pause"
    assert data.get("state_updated_by") == "operator"
    r = client.get(f"/v1/chats/{chat_id}/agents")
    primary = next(a for a in r.json()["agents"] if a["agent_id"] == "primary")
    assert primary["lifecycle_state"] == "paused"
    r = client.post(
        f"/v1/chats/{chat_id}/agents/primary/resume",
        json={"reason": "test resume"},
    )
    assert r.status_code == 200
    assert r.json().get("lifecycle_state") == "active"
    r = client.get(f"/v1/chats/{chat_id}/agents")
    primary = next(a for a in r.json()["agents"] if a["agent_id"] == "primary")
    assert primary["lifecycle_state"] == "active"


def test_quarantine_release_roundtrip(client, chat_with_agent):
    """POST quarantine then release; list shows quarantined then active."""
    chat_id = chat_with_agent
    r = client.post(
        f"/v1/chats/{chat_id}/agents/primary/quarantine",
        json={"reason": "drill"},
    )
    assert r.status_code == 200
    assert r.json().get("lifecycle_state") == "quarantined"
    r = client.post(f"/v1/chats/{chat_id}/agents/primary/release")
    assert r.status_code == 200
    assert r.json().get("lifecycle_state") == "active"


def test_post_message_returns_423_when_agent_paused(client, chat_with_agent):
    """When agent is paused, POST /chats/{id}/messages returns 423 agent_paused."""
    chat_id = chat_with_agent
    client.post(f"/v1/chats/{chat_id}/agents/primary/pause", json={"reason": "test"})
    r = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Should be blocked"},
    )
    assert r.status_code == 423
    data = r.json()
    assert data.get("detail", {}).get("code") == "agent_paused"


def test_post_message_returns_423_when_agent_quarantined(client, chat_with_agent):
    """When agent is quarantined, POST /chats/{id}/messages returns 423 agent_quarantined."""
    chat_id = chat_with_agent
    client.post(f"/v1/chats/{chat_id}/agents/primary/quarantine", json={"reason": "test"})
    r = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Should be blocked"},
    )
    assert r.status_code == 423
    data = r.json()
    assert data.get("detail", {}).get("code") == "agent_quarantined"


def test_pause_nonexistent_agent_returns_404(client):
    """POST pause for non-existent chat or agent returns 404."""
    r = client.post(
        "/v1/chats/nonexistent-chat-id/agents/primary/pause",
        json={},
    )
    assert r.status_code == 404
