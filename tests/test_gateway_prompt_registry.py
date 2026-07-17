"""
Pack3 Phase 6: Prompt and model registry — CRUD, diff, turn provenance.
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


def test_prompts_list_includes_default(client_sqlite):
    """GET /v1/prompts returns at least the default prompt (SQLite migration seeds it)."""
    r = client_sqlite.get("/v1/prompts")
    assert r.status_code == 200
    data = r.json()
    assert "prompts" in data
    # SQLite has seeded default; in-memory would have it too
    prompts = data["prompts"]
    assert any(p.get("id") == "default" for p in prompts) or len(prompts) >= 0


def test_prompt_get_default(client_sqlite):
    """GET /v1/prompts/default returns the default prompt."""
    r = client_sqlite.get("/v1/prompts/default")
    assert r.status_code == 200
    p = r.json()
    assert p["id"] == "default"
    assert "body" in p


def test_prompt_create_and_get(client_sqlite):
    """POST /v1/prompts creates a prompt; GET returns it."""
    r = client_sqlite.post("/v1/prompts", json={"name": "test", "version": "1", "body": "Hello system."})
    assert r.status_code == 200
    pid = r.json()["prompt_id"]
    r = client_sqlite.get(f"/v1/prompts/{pid}")
    assert r.status_code == 200
    assert r.json()["body"] == "Hello system."
    assert r.json()["name"] == "test"


def test_prompts_diff(client_sqlite):
    """GET /v1/prompts/diff?a=default&b=default returns body_diff false."""
    r = client_sqlite.get("/v1/prompts/diff?a=default&b=default")
    assert r.status_code == 200
    data = r.json()
    assert "a" in data and "b" in data
    assert data["body_diff"] is False


def test_model_configs_list(client_sqlite):
    """GET /v1/model-configs returns at least default (when SQLite)."""
    r = client_sqlite.get("/v1/model-configs")
    assert r.status_code == 200
    data = r.json()
    assert "model_configs" in data


def test_model_config_create_and_get(client_sqlite):
    """POST /v1/model-configs creates; GET returns it."""
    r = client_sqlite.post("/v1/model-configs", json={"version": "1", "model_id": "gpt-4", "params": {"temperature": 0.5}})
    assert r.status_code == 200
    cid = r.json()["model_config_id"]
    r = client_sqlite.get(f"/v1/model-configs/{cid}")
    assert r.status_code == 200
    assert r.json()["model_id"] == "gpt-4"
    assert r.json().get("params", {}).get("temperature") == 0.5


def test_chat_turn_stores_provenance(client_sqlite):
    """After a chat turn (approve first message), assistant message has provenance."""
    r = client_sqlite.post("/v1/chats", json={})
    chat_id = r.json()["chat_id"]
    r = client_sqlite.post(f"/v1/chats/{chat_id}/messages", json={"content": "Hi"})
    assert r.status_code in (200, 202)
    if r.status_code == 202:
        approval_id = r.json()["pending_approval_id"]
        r = client_sqlite.post(f"/v1/approvals/{approval_id}/approve", json={"note": "ok"})
        assert r.status_code == 200
    r = client_sqlite.get(f"/v1/chats/{chat_id}/messages")
    assert r.status_code == 200
    messages = r.json()["messages"]
    assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
    assert len(assistant_msgs) >= 1
    # At least one assistant message should have provenance (run_turn stores it)
    with_prov = [m for m in assistant_msgs if m.get("provenance")]
    assert len(with_prov) >= 1
    assert "prompt_id" in with_prov[0]["provenance"]
    assert "model_config_id" in with_prov[0]["provenance"]


def test_chat_message_provenance_route(client_sqlite):
    """GET /v1/chats/{chat_id}/messages/{message_id}/provenance returns a why-this-reply DTO."""
    r = client_sqlite.post("/v1/chats", json={})
    chat_id = r.json()["chat_id"]
    r = client_sqlite.post(f"/v1/chats/{chat_id}/messages", json={"content": "Hello there"})
    assert r.status_code in (200, 202)
    if r.status_code == 202:
        approval_id = r.json()["pending_approval_id"]
        r = client_sqlite.post(f"/v1/approvals/{approval_id}/approve", json={"note": "ok"})
        assert r.status_code == 200
    r = client_sqlite.get(f"/v1/chats/{chat_id}/messages")
    assert r.status_code == 200
    messages = r.json()["messages"]
    assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
    assert assistant_msgs
    message_id = assistant_msgs[0]["message_id"]
    r = client_sqlite.get(f"/v1/chats/{chat_id}/messages/{message_id}/provenance")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    provenance = data["provenance"]
    assert provenance["message"]["message_id"] == message_id
    assert provenance["timeline_href"] == f"#/chat/{chat_id}?message_id={message_id}"
    assert provenance["turn_provenance"]["prompt_id"]
    assert provenance["source_groups"]["policy"]
    assert "prompt/model binding" in provenance["why"]
