import os
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest

from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway.main import app
from hg_gateway.store import get_store
from hg_gateway import store as store_module


@pytest.fixture
def client(tmp_path):
    store_module._store = None
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[get_tenant_context] = lambda: type("TC", (), {"tenant_id": "default"})()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        app.dependency_overrides.pop(get_tenant_context, None)
        os.environ.pop("HG_GATEWAY_DB_PATH", None)
        store_module._store = None


@patch("hg_gateway.routes._requires_approval", return_value=False)
@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
def test_swarm_run_creates_orchestrator_workspace(mock_run_turn, _mock_requires_approval, client):
    mock_run_turn.side_effect = [
        type("Row", (), {"message_id": "m1", "chat_id": "child-1", "role": "assistant", "created_at": "t", "content": "One", "agent_id": "primary"})(),
        type("Row", (), {"message_id": "m2", "chat_id": "child-2", "role": "assistant", "created_at": "t", "content": "Two", "agent_id": "primary"})(),
    ]

    response = client.post("/v1/swarm/run", json={"task": "Say hello", "count": 2})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["parent_chat_id"]
    workspace = client.get(f"/v1/swarms/{payload['swarm_run_id']}")
    assert workspace.status_code == 200, workspace.text
    body = workspace.json()
    assert body["orchestrator"]["chat_id"] == payload["parent_chat_id"]
    assert body["orchestrator"]["swarm_role"] == "orchestrator"
    assert len(body["members"]) == 2


def test_delete_swarm_deletes_orchestrator_and_members(client):
    store = get_store()
    swarm_run_id = "swarm-123"
    parent = store.chat_create("default", title="Master", swarm_run_id=swarm_run_id, swarm_role="orchestrator")
    child = store.chat_create("default", title="Member", swarm_run_id=swarm_run_id, swarm_role="entity")
    store.message_add("default", parent, "user", "master")
    store.message_add("default", child, "user", "child")

    response = client.delete(f"/v1/swarms/{swarm_run_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["deleted_count"] == 2
    assert set(body["deleted_chat_ids"]) == {parent, child}
    remaining = client.get("/v1/chats").json()["chats"]
    assert remaining == []


def test_archive_chat_hides_from_default_list_and_restore_returns_it(client):
    store = get_store()
    chat_id = store.chat_create("default", title="Archive me")

    archived = client.post(f"/v1/chats/{chat_id}/archive", json={"reason": "manual"})
    assert archived.status_code == 200, archived.text
    assert archived.json()["archived"] is True

    active = client.get("/v1/chats").json()["chats"]
    assert active == []

    archived_only = client.get("/v1/chats?include_archived=true&archived_only=true").json()["chats"]
    assert len(archived_only) == 1
    assert archived_only[0]["chat_id"] == chat_id
    assert archived_only[0]["archive_reason"] == "manual"

    restored = client.post(f"/v1/chats/{chat_id}/restore")
    assert restored.status_code == 200, restored.text
    assert restored.json()["archived"] is False

    active = client.get("/v1/chats").json()["chats"]
    assert len(active) == 1
    assert active[0]["chat_id"] == chat_id


def test_archive_swarm_hides_group_and_restore_returns_it(client):
    store = get_store()
    swarm_run_id = "swarm-archive-1"
    parent = store.chat_create("default", title="Master", swarm_run_id=swarm_run_id, swarm_role="orchestrator")
    child = store.chat_create("default", title="Member", swarm_run_id=swarm_run_id, swarm_role="entity")

    archived = client.post(f"/v1/swarms/{swarm_run_id}/archive", json={"reason": "manual"})
    assert archived.status_code == 200, archived.text
    assert archived.json()["updated_count"] == 2

    active = client.get("/v1/chats").json()["chats"]
    assert active == []

    archived_only = client.get("/v1/chats?include_archived=true&archived_only=true").json()["chats"]
    assert {item["chat_id"] for item in archived_only} == {parent, child}

    restored = client.post(f"/v1/swarms/{swarm_run_id}/restore")
    assert restored.status_code == 200, restored.text
    assert restored.json()["updated_count"] == 2

    active = client.get("/v1/chats").json()["chats"]
    assert {item["chat_id"] for item in active} == {parent, child}


def test_trash_chat_hides_from_default_list_and_restore_returns_it(client):
    store = get_store()
    chat_id = store.chat_create("default", title="Delete me softly")

    trashed = client.post(f"/v1/chats/{chat_id}/trash", json={"reason": "manual"})
    assert trashed.status_code == 200, trashed.text
    assert trashed.json()["deleted"] is True

    active = client.get("/v1/chats").json()["chats"]
    assert active == []

    deleted_only = client.get("/v1/chats?include_deleted=true&deleted_only=true").json()["chats"]
    assert len(deleted_only) == 1
    assert deleted_only[0]["chat_id"] == chat_id
    assert deleted_only[0]["delete_reason"] == "manual"
    assert deleted_only[0]["restore_deadline_at"]

    restored = client.post(f"/v1/chats/{chat_id}/restore")
    assert restored.status_code == 200, restored.text
    assert restored.json()["deleted"] is False

    active = client.get("/v1/chats").json()["chats"]
    assert len(active) == 1
    assert active[0]["chat_id"] == chat_id


def test_trash_swarm_hides_group_and_restore_returns_it(client):
    store = get_store()
    swarm_run_id = "swarm-trash-1"
    parent = store.chat_create("default", title="Master", swarm_run_id=swarm_run_id, swarm_role="orchestrator")
    child = store.chat_create("default", title="Member", swarm_run_id=swarm_run_id, swarm_role="entity")

    trashed = client.post(f"/v1/swarms/{swarm_run_id}/trash", json={"reason": "manual"})
    assert trashed.status_code == 200, trashed.text
    assert trashed.json()["updated_count"] == 2

    active = client.get("/v1/chats").json()["chats"]
    assert active == []

    deleted_only = client.get("/v1/chats?include_deleted=true&deleted_only=true").json()["chats"]
    assert {item["chat_id"] for item in deleted_only} == {parent, child}

    restored = client.post(f"/v1/swarms/{swarm_run_id}/restore")
    assert restored.status_code == 200, restored.text
    assert restored.json()["updated_count"] == 2

    active = client.get("/v1/chats").json()["chats"]
    assert {item["chat_id"] for item in active} == {parent, child}


@patch("hg_gateway.routes._generate_chat_title", new_callable=AsyncMock, return_value="Iran strike reaction")
@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
def test_post_message_auto_titles_generic_chat(mock_run_turn, _mock_title, client):
    store = get_store()
    chat_id = store.chat_create("default", title="New chat")
    mock_run_turn.return_value = type(
        "Row",
        (),
        {"message_id": "a1", "chat_id": chat_id, "role": "assistant", "created_at": "t", "content": "Reply", "agent_id": "primary"},
    )()

    response = client.post(f"/v1/chats/{chat_id}/messages", json={"content": "Give me your reaction in two paragraphs."})

    assert response.status_code == 202 or response.status_code == 200
    chat = client.get(f"/v1/chats/{chat_id}").json()
    assert chat["title"] == "Iran strike reaction"


@patch("hg_gateway.routes._generate_chat_title", new_callable=AsyncMock, return_value="Should not apply")
@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
def test_post_message_preserves_custom_title(mock_run_turn, _mock_title, client):
    store = get_store()
    chat_id = store.chat_create("default", title="Board prep")
    mock_run_turn.return_value = type(
        "Row",
        (),
        {"message_id": "a1", "chat_id": chat_id, "role": "assistant", "created_at": "t", "content": "Reply", "agent_id": "primary"},
    )()

    response = client.post(f"/v1/chats/{chat_id}/messages", json={"content": "Give me your reaction in two paragraphs."})

    assert response.status_code in (200, 202)
    chat = client.get(f"/v1/chats/{chat_id}").json()
    assert chat["title"] == "Board prep"
