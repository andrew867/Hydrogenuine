import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from hg_gateway.auth import verify_api_key
from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.orchestration import run_turn
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
        os.environ.pop("HG_PERSONA_COGNITIVE_AUTONOMY_ENABLED", None)
        store_module._store = None


@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
@patch("hg_gateway.routes._requires_approval", return_value=False)
def test_gateway_injects_autonomy_directives_into_persona_prompt(_mock_approval, mock_run_turn, client):
    store = get_store()
    chat_id = store.chat_create("default", title="Autonomy", fingerprint_id="ada_lovelace")
    mock_run_turn.return_value = type(
        "Row",
        (),
        {"message_id": "m1", "chat_id": chat_id, "role": "assistant", "created_at": "t", "content": "Reply", "agent_id": "primary"},
    )()

    response = client.post(f"/v1/chats/{chat_id}/messages", json={"content": "Explain what the machine could become."})

    assert response.status_code == 200, response.text
    system_prompt = mock_run_turn.await_args.kwargs["messages_for_llm"][0]["content"]
    assert "Autonomy:" in system_prompt
    assert "uncertainty=" in system_prompt


@pytest.mark.asyncio
async def test_run_turn_persists_autonomy_analytics(monkeypatch, tmp_path):
    store_module._store = None
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    try:
        store = get_store()
        chat_id = store.chat_create("default", title="Autonomy", fingerprint_id="ada_lovelace")
        store.message_add("default", chat_id, "user", "Explain what the machine could become.")

        async def mock_stream(*, messages, **kwargs):
            yield "The machine could become a general engine for symbols."

        class MockRegistry:
            def stream_complete(self, *args, **kwargs):
                return mock_stream(*args, **kwargs)

        import hg_llm

        monkeypatch.setattr(hg_llm, "get_default_registry", lambda: MockRegistry())
        row = await run_turn(
            "default",
            chat_id,
            agent_id="primary",
            agent_label="Primary",
            messages_for_llm=[{"role": "user", "content": "Explain what the machine could become."}],
            emit=lambda _ev, _payload: None,
        )

        rows = store.persona_autonomy_list("default", chat_id=chat_id)
        assert row.message_id
        assert len(rows) == 1
        assert rows[0]["turn_id"] == row.message_id
        assert rows[0]["arc_state"] in {"opening", "building", "deepening"}
        assert rows[0]["uncertainty_level"]
    finally:
        os.environ.pop("HG_GATEWAY_DB_PATH", None)
        os.environ.pop("HG_GATEWAY_STORE", None)
        store_module._store = None
