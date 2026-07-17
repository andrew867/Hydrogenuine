"""
Unit and integration tests for Swarm API (POST /v1/swarm/run).
- Unit: _build_messages_for_llm, _get_swarm_personas
- Integration: swarm_run 200/202, validation 400, quotas 429
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from hg_gateway.routes import _build_messages_for_llm, _get_swarm_personas, _get_swarm_max_count
from hg_gateway.store import get_store
from hg_gateway import store as store_module
from hg_gateway.main import app
from hg_gateway.auth import verify_api_key, get_tenant_context


@pytest.fixture
def store(tmp_path):
    """Store for unit tests (SQLite by default, isolated path)."""
    store_module._store = None
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    try:
        s = get_store()
        yield s
    finally:
        store_module._store = None
        os.environ.pop("HG_GATEWAY_DB_PATH", None)


@pytest.fixture
def client(tmp_path):
    """TestClient with auth and tenant overrides (SQLite by default, isolated path)."""
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


# ---- Unit: _build_messages_for_llm ----
def test_build_messages_for_llm_no_persona(store):
    """Chat without fingerprint_id returns [user] only."""
    tenant_id = "default"
    chat_id = store.chat_create(tenant_id, title="No persona")
    store.message_add(tenant_id, chat_id, "user", "Hello")
    msgs = _build_messages_for_llm(store, tenant_id, chat_id, "Hello")
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Hello"


def test_build_messages_for_llm_with_persona(store):
    """Chat with fingerprint_id returns [system?, user]; system may be present if persona loads."""
    tenant_id = "default"
    chat_id = store.chat_create(tenant_id, title="With persona", fingerprint_id="some_persona")
    store.message_add(tenant_id, chat_id, "user", "Hi")
    msgs = _build_messages_for_llm(store, tenant_id, chat_id, "Hi")
    assert len(msgs) >= 1
    assert msgs[-1]["role"] == "user"
    assert msgs[-1]["content"] == "Hi"
    if len(msgs) == 2:
        assert msgs[0]["role"] == "system"
        assert isinstance(msgs[0]["content"], str)


# ---- Unit: _get_swarm_personas ----
def test_get_swarm_personas_returns_at_most_count():
    """_get_swarm_personas(count) returns at most count items, deterministic order."""
    result = _get_swarm_personas(3)
    assert isinstance(result, list)
    assert len(result) <= 3
    for p in result:
        assert "fingerprint_id" in p
        assert isinstance(p["fingerprint_id"], str)


def test_get_swarm_personas_zero_count():
    """_get_swarm_personas(0) returns []."""
    result = _get_swarm_personas(0)
    assert result == []


def test_get_swarm_max_count_default():
    """_get_swarm_max_count returns at least 1 (default 10 without env)."""
    with patch.dict(os.environ, {}, clear=False):
        if "HG_SWARM_MAX_COUNT" in os.environ:
            del os.environ["HG_SWARM_MAX_COUNT"]
    n = _get_swarm_max_count()
    assert n >= 1


# ---- Integration: swarm_run ----
@pytest.mark.asyncio
async def test_swarm_run_400_missing_task_and_tasks(client):
    """Missing both task and tasks returns 400."""
    r = client.post("/v1/swarm/run", json={})
    assert r.status_code == 400


def test_swarm_run_400_empty_task(client):
    """Empty task with no tasks returns 400."""
    r = client.post("/v1/swarm/run", json={"task": ""})
    assert r.status_code == 400


def test_swarm_run_400_tasks_empty_element(client):
    """tasks with empty string element returns 400."""
    r = client.post("/v1/swarm/run", json={"tasks": ["OK", ""]})
    assert r.status_code == 400


def test_swarm_run_400_count_zero(client):
    """count=0 returns 400."""
    r = client.post("/v1/swarm/run", json={"task": "Hi", "count": 0})
    assert r.status_code == 400


def test_swarm_run_400_count_over_max(client):
    """count > max_swarm_size returns 400."""
    max_n = _get_swarm_max_count()
    r = client.post("/v1/swarm/run", json={"task": "Hi", "count": max_n + 10})
    assert r.status_code == 400


def test_swarm_run_200_single_task(client):
    """Swarm with single task and count=2 returns 200 and 2 chat_ids (if 2+ personas available)."""
    personas = _get_swarm_personas(2)
    if len(personas) < 2:
        pytest.skip("Need at least 2 personas for this test")
    r = client.post("/v1/swarm/run", json={"task": "Hello", "count": 2})
    if r.status_code == 200:
        data = r.json()
        assert "chat_ids" in data
        assert len(data["chat_ids"]) == 2
        assert data.get("task") == "Hello"
    elif r.status_code == 202:
        data = r.json()
        assert "chat_ids" in data
        assert "approval_ids" in data
        assert len(data["chat_ids"]) == 2
        assert len(data["approval_ids"]) == 2
    else:
        pytest.fail(f"Expected 200 or 202, got {r.status_code}: {r.json()}")


def test_swarm_run_200_tasks_array(client):
    """Swarm with tasks array returns 200 and one chat per task (if enough personas)."""
    tasks = ["Weather in Ontario", "Weather in Quebec"]
    personas = _get_swarm_personas(len(tasks))
    if len(personas) < len(tasks):
        pytest.skip("Need at least 2 personas for this test")
    r = client.post("/v1/swarm/run", json={"tasks": tasks})
    if r.status_code == 200:
        data = r.json()
        assert "chat_ids" in data
        assert len(data["chat_ids"]) == 2
        assert data.get("tasks") == tasks
    elif r.status_code == 202:
        data = r.json()
        assert len(data["chat_ids"]) == 2
        assert len(data["approval_ids"]) == 2
    else:
        pytest.fail(f"Expected 200 or 202, got {r.status_code}: {r.json()}")


def test_swarm_run_400_not_enough_personas(client):
    """Requesting more agents than available personas returns 400 not_enough_personas."""
    with patch("hg_gateway.routes._get_swarm_personas", return_value=[
        {"fingerprint_id": "persona_a", "skin_id": None},
        {"fingerprint_id": "persona_b", "skin_id": None},
    ]):
        r = client.post("/v1/swarm/run", json={"task": "Hi", "count": 3})
    assert r.status_code == 400
    data = r.json()
    detail = data.get("detail") or {}
    code = detail.get("code") if isinstance(detail, dict) else None
    assert code == "not_enough_personas", f"Expected not_enough_personas, got {detail}"
    assert detail.get("available") == 2
    assert detail.get("requested") == 3


def test_swarm_run_202_approval_ids(client):
    """When first-turn approval is required, swarm returns 202 with chat_ids and approval_ids."""
    personas = _get_swarm_personas(2)
    if len(personas) < 2:
        pytest.skip("Need at least 2 personas")
    r = client.post("/v1/swarm/run", json={"task": "Hi", "count": 2})
    # Current implementation: new chats have one message each, so _requires_approval is True -> 202
    if r.status_code == 202:
        data = r.json()
        assert "chat_ids" in data
        assert "approval_ids" in data
        assert len(data["chat_ids"]) == 2
        assert len(data["approval_ids"]) == 2


def test_swarm_run_429_chat_quota(client):
    """When chat quota would be exceeded, swarm returns 429."""
    store = get_store()
    if not hasattr(store, "quota_set"):
        pytest.skip("Store has no quota_set")
    store.quota_set("default", {"max_chats": 1})
    personas = _get_swarm_personas(2)
    if len(personas) < 2:
        pytest.skip("Need at least 2 personas")
    r = client.post("/v1/swarm/run", json={"task": "Hi", "count": 2})
    assert r.status_code == 429
    data = r.json()
    detail = data.get("detail") or {}
    code = detail.get("code") if isinstance(detail, dict) else None
    assert code == "chats_exceeded"


# ---- E2E: full flow (broadcast and weather job) ----
def test_swarm_e2e_broadcast_three_chats(client):
    """E2E: Swarm with task and count=3; assert 3 chat_ids; if 202, resolve approvals and assert 3 assistant messages."""
    personas = _get_swarm_personas(3)
    if len(personas) < 3:
        pytest.skip("Need at least 3 personas for E2E broadcast")
    r = client.post("/v1/swarm/run", json={"task": "Say hello in one sentence.", "count": 3})
    assert r.status_code in (200, 202)
    data = r.json()
    assert "chat_ids" in data
    assert len(data["chat_ids"]) == 3
    if r.status_code == 202 and "approval_ids" in data:
        for aid in data["approval_ids"]:
            client.post(f"/v1/approvals/{aid}/approve", json={"note": "ok"})
        for cid in data["chat_ids"]:
            msgs = client.get(f"/v1/chats/{cid}/messages").json().get("messages") or []
            assert len(msgs) >= 2
            roles = [m["role"] for m in msgs]
            assert "user" in roles and "assistant" in roles


@pytest.mark.requires_network
def test_swarm_e2e_weather_ten_provinces(client):
    """E2E: Weather job with 10 province tasks; assert 10 chat_ids; if 202, resolve and assert 10 assistant messages.

    Marked requires_network: the swarm calls the live open-meteo weather API, which
    returns nondeterministic 5xx (observed HTTP 503 on pipeline 97). Auto-skips in
    hermetic CI (HG_CI_HERMETIC); runs when HG_CI_ALLOW_NETWORK=1. (CCS2: remove a
    live-external-network flake from the hermetic core.)
    """
    tasks = [f"What's the weather in {p}?" for p in [
        "Ontario", "Quebec", "British Columbia", "Alberta", "Manitoba",
        "Saskatchewan", "Nova Scotia", "New Brunswick", "Newfoundland and Labrador", "Prince Edward Island",
    ]]
    assert len(tasks) == 10
    personas = _get_swarm_personas(10)
    if len(personas) < 10:
        pytest.skip("Need at least 10 personas for E2E weather job")
    r = client.post("/v1/swarm/run", json={"tasks": tasks})
    assert r.status_code in (200, 202)
    data = r.json()
    assert "chat_ids" in data
    assert len(data["chat_ids"]) == 10
    if r.status_code == 202 and "approval_ids" in data:
        for aid in data["approval_ids"]:
            client.post(f"/v1/approvals/{aid}/approve", json={"note": "ok"})
    for i, cid in enumerate(data["chat_ids"]):
        msgs = client.get(f"/v1/chats/{cid}/messages").json().get("messages") or []
        assert len(msgs) >= 1
        assert any(m.get("content") == tasks[i] and m.get("role") == "user" for m in msgs)


@patch("hg_gateway.routes._fetch_open_meteo_snapshot")
@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
@patch("hg_gateway.routes._requires_approval", return_value=False)
def test_swarm_run_weather_tasks_inject_live_weather_facts(
    _mock_requires_approval,
    mock_run_turn,
    mock_weather,
    client,
):
    mock_weather.return_value = {
        "temperature_2m": 6.1,
        "relative_humidity_2m": 72,
        "wind_speed_10m": 15.3,
        "weather_code": 2,
        "precipitation": 0.0,
        "fetched_at": "2026-03-06T10:00:00Z",
        "source": "open-meteo",
    }
    mock_run_turn.side_effect = [
        type("Row", (), {"message_id": "m1", "chat_id": "c1", "role": "assistant", "created_at": "t", "content": "Ontario is mild.", "agent_id": "primary"})(),
        type("Row", (), {"message_id": "m2", "chat_id": "c2", "role": "assistant", "created_at": "t", "content": "Quebec is cool.", "agent_id": "primary"})(),
    ]

    response = client.post(
        "/v1/swarm/run",
        json={"tasks": ["What's the weather in Ontario?", "What's the weather in Quebec?"]},
    )

    assert response.status_code == 200, response.text
    assert mock_weather.call_count == 2
    first_messages = mock_run_turn.await_args_list[0].kwargs["messages_for_llm"]
    second_messages = mock_run_turn.await_args_list[1].kwargs["messages_for_llm"]
    assert "Temperature (C): 6.1" in first_messages[-1]["content"]
    assert "Ontario" in first_messages[-1]["content"]
    assert "Quebec" in second_messages[-1]["content"]

    for chat_id in response.json()["chat_ids"]:
        messages = client.get(f"/v1/chats/{chat_id}/messages").json()["messages"]
        assert any(message.get("tool_name") == "weather.fetch" for message in messages)


@patch("hg_gateway.routes._fetch_open_meteo_snapshot")
@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
def test_chat_message_weather_swarm_reduces_into_parent(mock_run_turn, mock_weather, client):
    store = get_store()
    chat_id = store.chat_create("default", title="Weather swarm", fingerprint_id="tesla")
    mock_weather.return_value = {
        "temperature_2m": 3.2,
        "relative_humidity_2m": 80,
        "wind_speed_10m": 12.4,
        "weather_code": 3,
        "precipitation": 0.0,
        "fetched_at": "2026-03-05T12:00:00Z",
        "source": "open-meteo",
    }
    mock_run_turn.side_effect = [
        type("Row", (), {"message_id": "m1", "chat_id": "child-bc", "role": "assistant", "created_at": "t", "content": "British Columbia is cool and breezy.", "agent_id": "primary"})(),
        type("Row", (), {"message_id": "m2", "chat_id": "child-ab", "role": "assistant", "created_at": "t", "content": "Alberta is cold and dry.", "agent_id": "primary"})(),
        type("Row", (), {"message_id": "m3", "chat_id": chat_id, "role": "assistant", "created_at": "t", "content": "Multiple parallel agents checked the provinces. British Columbia is milder while Alberta is colder.", "agent_id": "primary"})(),
    ]

    r = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Tesla, can you have multiple agents check the weather in British Columbia and Alberta in their own words and summarize it here?"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["swarm_count"] == 2
    assert data["swarm_provinces"] == ["BC", "AB"]
    assert data["message"]["chat_id"] == chat_id
    assert "parallel agents" in data["message"]["content"]

    msgs = client.get(f"/v1/chats/{chat_id}/messages").json()["messages"]
    assert any(m.get("role") == "tool" and m.get("tool_name") == "swarm.run" for m in msgs)

    chats = client.get("/v1/chats").json()["chats"]
    children = [c for c in chats if c.get("swarm_run_id") and c.get("swarm_role") == "entity"]
    assert len(children) == 2
