import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway.main import app
from hg_gateway import routes as gateway_routes
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


@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
@patch("hg_gateway.routes._requires_approval", return_value=False)
@patch("hg_gateway.routes._fetch_open_meteo_snapshot")
def test_post_message_local_weather_uses_detected_timezone_default(
    mock_weather,
    _mock_requires_approval,
    mock_run_turn,
    client,
):
    store = get_store()
    chat_id = store.chat_create("default", title="Weather", fingerprint_id="newfoundland_bayman")
    mock_weather.return_value = {
        "temperature_2m": 3.5,
        "relative_humidity_2m": 84,
        "wind_speed_10m": 18,
        "weather_code": 3,
        "precipitation": 0.0,
        "fetched_at": "2026-03-06T14:00:00Z",
        "source": "open-meteo",
    }
    mock_run_turn.return_value = type(
        "Row",
        (),
        {
            "message_id": "m1",
            "chat_id": chat_id,
            "role": "assistant",
            "created_at": "t",
            "content": "St. John's is sitting around 3.5 C with a stiff breeze off the harbour.",
            "agent_id": "primary",
        },
    )()

    response = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "How's the weather today?"},
        headers={"X-HG-Timezone": "America/St_Johns"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["local_weather"]["province_code"] == "NL"
    messages = client.get(f"/v1/chats/{chat_id}/messages").json()["messages"]
    assert any(message.get("tool_name") == "weather.fetch" for message in messages)
    prompt = mock_run_turn.await_args.kwargs["messages_for_llm"][-1]["content"]
    assert "St. John's" in prompt
    assert "Do not say you lack tools" in prompt


@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
@patch("hg_gateway.routes._requires_approval", return_value=False)
@patch("hg_gateway.routes._geocode_place")
@patch("hg_gateway.routes._fetch_open_meteo_snapshot")
def test_post_message_weather_for_explicit_place_returns_that_place(
    mock_weather,
    mock_geocode,
    _mock_requires_approval,
    mock_run_turn,
    client,
):
    store = get_store()
    chat_id = store.chat_create("default", title="Weather elsewhere", fingerprint_id="newfoundland_bayman")
    mock_geocode.return_value = {
        "place_name": "Paris",
        "place_label": "Paris, Ile-de-France, France",
        "region_name": "Ile-de-France",
        "country": "France",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "timezone": "Europe/Paris",
        "is_default": False,
    }
    mock_weather.return_value = {
        "temperature_2m": 17.6,
        "relative_humidity_2m": 59,
        "wind_speed_10m": 6.8,
        "weather_code": 3,
        "precipitation": 0.0,
        "fetched_at": "2026-03-06T18:15:00Z",
        "source": "open-meteo",
    }
    mock_run_turn.return_value = type(
        "Row",
        (),
        {
            "message_id": "m-explicit-place",
            "chat_id": chat_id,
            "role": "assistant",
            "created_at": "t",
            "content": "Paris is mild and mostly cloudy.",
            "agent_id": "primary",
        },
    )()

    response = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "What is the weather in Paris right now?"},
        headers={"X-HG-Timezone": "America/St_Johns"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["local_weather"]["place_name"] == "Paris"
    assert data["local_weather"]["place_label"] == "Paris, Ile-de-France, France"
    prompt = mock_run_turn.await_args.kwargs["messages_for_llm"][-1]["content"]
    assert "Paris, Ile-de-France, France" in prompt


@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
@patch("hg_gateway.routes._requires_approval", return_value=False)
@patch("hg_gateway.routes.gateway_tools.invoke_tool")
def test_post_message_local_news_triggers_search_and_fetch(
    mock_invoke_tool,
    _mock_requires_approval,
    mock_run_turn,
    client,
):
    store = get_store()
    chat_id = store.chat_create("default", title="News", fingerprint_id="newfoundland_bayman")

    def _tool_result(tool_name, inputs, **_kwargs):
        if tool_name == "brave.news.search":
            return {
                "ok": True,
                "outputs": {
                    "data": {
                        "query": inputs["query"],
                        "results": [
                            {"title": "VOCM Story One", "url": "https://vocm.com/story1", "description": "Story one summary."},
                            {"title": "VOCM Story Two", "url": "https://vocm.com/story2", "description": "Story two summary."},
                        ],
                    }
                },
            }
        if tool_name == "search.fetch_url":
            return {
                "ok": True,
                "outputs": {
                    "data": {
                        "url": inputs["url"],
                        "final_url": inputs["url"],
                        "content_preview": f"Fetched preview for {inputs['url']}",
                    }
                },
            }
        raise AssertionError(f"Unexpected tool call: {tool_name}")

    mock_invoke_tool.side_effect = _tool_result
    async def _mock_run_turn(*_args, **_kwargs):
        return store.message_add(
            "default",
            chat_id,
            "assistant",
            "The main VOCM stories this week centre on provincial politics and local response.",
            agent_id="primary",
        )

    mock_run_turn.side_effect = _mock_run_turn

    response = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Can you search online and find me the top VOCM news stories of the week?"},
        headers={"X-HG-Timezone": "America/St_Johns"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["search"]["kind"] == "news"
    assert "VOCM news Newfoundland and Labrador this week" == data["search"]["query"]
    assert data["search"]["plan_template"] == "planned_research_summary_v1"
    assert data["message"]["sources"][0]["url"] == "https://vocm.com/story1"
    assert data["message"]["sources"][0]["title"] == "VOCM Story One"
    assert any(call.args[0] == "brave.news.search" for call in mock_invoke_tool.call_args_list)
    assert any(call.args[0] == "search.fetch_url" for call in mock_invoke_tool.call_args_list)
    messages = client.get(f"/v1/chats/{chat_id}/messages").json()["messages"]
    assert any(message.get("tool_name") == "planner.plan" for message in messages)
    assert any(message.get("tool_name") == "brave.news.search" for message in messages)
    assert any(message.get("tool_name") == "search.fetch_url" for message in messages)
    assistant = next(message for message in messages if message.get("role") == "assistant")
    assert assistant["sources"][0]["url"] == "https://vocm.com/story1"
    assert assistant["sources"][0]["title"] == "VOCM Story One"


@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
@patch("hg_gateway.routes._requires_approval", return_value=False)
@patch("hg_gateway.routes.gateway_tools.invoke_tool")
def test_post_message_local_news_merges_query_variants_and_dedupes_sources(
    mock_invoke_tool,
    _mock_requires_approval,
    mock_run_turn,
    client,
):
    store = get_store()
    chat_id = store.chat_create("default", title="News merge", fingerprint_id="newfoundland_bayman")

    def _tool_result(tool_name, inputs, **_kwargs):
        if tool_name == "brave.news.search":
            query = inputs["query"]
            if query.endswith(" latest"):
                return {
                    "ok": True,
                    "outputs": {
                        "data": {
                            "query": query,
                            "results": [
                                {"title": "VOCM Story One", "url": "https://vocm.com/story1?utm_source=test", "description": "Updated story one summary."},
                                {"title": "VOCM Story Three", "url": "https://vocm.com/story3", "description": "Story three summary."},
                            ],
                        }
                    },
                }
            return {
                "ok": True,
                "outputs": {
                    "data": {
                        "query": query,
                        "results": [
                            {"title": "VOCM Story One", "url": "https://vocm.com/story1", "description": "Story one summary."},
                            {"title": "VOCM Story Two", "url": "https://vocm.com/story2", "description": "Story two summary."},
                        ],
                    }
                },
            }
        if tool_name == "search.fetch_url":
            return {
                "ok": True,
                "outputs": {
                    "data": {
                        "url": inputs["url"],
                        "final_url": inputs["url"],
                        "content_preview": f"Fetched preview for {inputs['url']}",
                    }
                },
            }
        raise AssertionError(f"Unexpected tool call: {tool_name}")

    mock_invoke_tool.side_effect = _tool_result

    async def _mock_run_turn(*_args, **_kwargs):
        return store.message_add(
            "default",
            chat_id,
            "assistant",
            "Merged the strongest local stories across multiple search passes.",
            agent_id="primary",
        )

    mock_run_turn.side_effect = _mock_run_turn

    response = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Can you search online and find me the top VOCM news stories of the week?"},
        headers={"X-HG-Timezone": "America/St_Johns"},
    )

    assert response.status_code == 200, response.text
    search_calls = [call for call in mock_invoke_tool.call_args_list if call.args[0] == "brave.news.search"]
    assert len(search_calls) >= 2
    fetch_calls = [call for call in mock_invoke_tool.call_args_list if call.args[0] == "search.fetch_url"]
    fetched_urls = [call.args[1]["url"] for call in fetch_calls]
    assert "https://vocm.com/story1?utm_source=test" not in fetched_urls
    assert fetched_urls[:3] == ["https://vocm.com/story1", "https://vocm.com/story2", "https://vocm.com/story3"]
    sources = response.json()["message"]["sources"]
    urls = [source["url"] for source in sources]
    assert urls.count("https://vocm.com/story1") == 1
    assert "https://vocm.com/story3" in urls


@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
@patch("hg_gateway.routes._requires_approval", return_value=False)
@patch("hg_gateway.routes.gateway_tools.invoke_tool")
def test_post_message_global_news_request_does_not_fall_back_to_local_region(
    mock_invoke_tool,
    _mock_requires_approval,
    mock_run_turn,
    client,
):
    store = get_store()
    chat_id = store.chat_create("default", title="Global research", fingerprint_id="dale_gribble")

    def _tool_result(tool_name, inputs, **_kwargs):
        if tool_name == "brave.news.search":
            return {
                "ok": True,
                "outputs": {
                    "data": {
                        "query": inputs["query"],
                        "results": [
                            {"title": "US expands surveillance debate", "url": "https://example.com/us-flock", "description": "Federal and local policy scrutiny rises."},
                        ],
                    }
                },
            }
        if tool_name == "search.fetch_url":
            return {
                "ok": True,
                "outputs": {"data": {"url": inputs["url"], "final_url": inputs["url"], "content_preview": "U.S. government and Flock camera reporting."}},
            }
        raise AssertionError(f"Unexpected tool call: {tool_name}")

    mock_invoke_tool.side_effect = _tool_result
    mock_run_turn.return_value = type(
        "Row",
        (),
        {
            "message_id": "m-global",
            "chat_id": chat_id,
            "role": "assistant",
            "created_at": "t",
            "content": "The U.S. surveillance and Flock camera story is widening.",
            "agent_id": "primary",
        },
    )()

    response = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "dale whats going on today with the us government and what the hell are they doing to their own people with flock cameras everywhere?"},
        headers={"X-HG-Timezone": "America/St_Johns"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["search"]["kind"] == "news"
    assert "newfoundland" not in data["search"]["query"].lower()
    assert "labrador" not in data["search"]["query"].lower()
    assert "us government" in data["search"]["query"].lower() or "flock cameras" in data["search"]["query"].lower()


@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
@patch("hg_gateway.routes._requires_approval", return_value=True)
@patch("hg_gateway.routes.gateway_tools.invoke_tool")
def test_local_news_approval_resume_executes_grounded_search(
    mock_invoke_tool,
    _mock_requires_approval,
    mock_run_turn,
    client,
):
    store = get_store()
    chat_id = store.chat_create("default", title="Approve search", fingerprint_id="newfoundland_bayman")

    def _tool_result(tool_name, inputs, **_kwargs):
        if tool_name == "brave.news.search":
            return {
                "ok": True,
                "outputs": {
                    "data": {
                        "query": inputs["query"],
                        "results": [{"title": "VOCM Story", "url": "https://vocm.com/story", "description": "Story summary."}],
                    }
                },
            }
        return {
            "ok": True,
            "outputs": {
                "data": {
                    "url": inputs["url"],
                    "final_url": inputs["url"],
                    "content_preview": "Fetched preview",
                }
            },
        }

    mock_invoke_tool.side_effect = _tool_result
    async def _mock_run_turn(*_args, **_kwargs):
        return store.message_add(
            "default",
            chat_id,
            "assistant",
            "Here are the VOCM stories that stood out this week.",
            agent_id="primary",
        )

    mock_run_turn.side_effect = _mock_run_turn

    initial = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Find me the top VOCM news stories this week."},
        headers={"X-HG-Timezone": "America/St_Johns"},
    )
    assert initial.status_code == 202, initial.text
    approval_id = initial.json()["pending_approval_id"]
    approval = store.approval_get("default", approval_id)
    assert approval["payload"]["type"] == "local_search_chat_turn"
    approved = client.post(f"/v1/approvals/{approval_id}/approve", json={"note": "ok"})
    assert approved.status_code == 200, approved.text
    assert approved.json()["continued"] is True
    assert approved.json()["search"]["plan_template"] == "planned_research_summary_v1"
    assert approved.json()["message"]["sources"][0]["url"] == "https://vocm.com/story"
    messages = client.get(f"/v1/chats/{chat_id}/messages").json()["messages"]
    assert any(message.get("tool_name") == "planner.plan" for message in messages)
    assert any(message.get("tool_name") == "brave.news.search" for message in messages)
    assistant = next(message for message in messages if message.get("role") == "assistant")
    assert assistant["sources"][0]["url"] == "https://vocm.com/story"


@patch("hg_gateway.routes.run_turn", new_callable=AsyncMock)
@patch("hg_gateway.routes._requires_approval", return_value=False)
@patch("hg_gateway.routes.gateway_tools.invoke_tool")
def test_post_message_world_news_query_does_not_collapse_to_local_news(
    mock_invoke_tool,
    _mock_requires_approval,
    mock_run_turn,
    client,
):
    store = get_store()
    chat_id = store.chat_create("default", title="World news", fingerprint_id="newfoundland_bayman")

    def _tool_result(tool_name, inputs, **_kwargs):
        if tool_name == "brave.news.search":
            assert "iran" in inputs["query"].lower()
            assert "newfoundland and labrador" not in inputs["query"].lower()
            return {
                "ok": True,
                "outputs": {
                    "data": {
                        "query": inputs["query"],
                        "results": [
                            {"title": "Reuters Iran strike story", "url": "https://example.com/reuters", "description": "Summary one."}
                        ],
                    }
                },
            }
        if tool_name == "search.fetch_url":
            return {
                "ok": True,
                "outputs": {
                    "data": {
                        "url": inputs["url"],
                        "final_url": inputs["url"],
                        "content_preview": "Reuters reported on the U.S. strike and Iranian response.",
                    }
                },
            }
        raise AssertionError(f"Unexpected tool call: {tool_name}")

    mock_invoke_tool.side_effect = _tool_result
    mock_run_turn.return_value = type(
        "Row",
        (),
        {
            "message_id": "m-world",
            "chat_id": chat_id,
            "role": "assistant",
            "created_at": "t",
            "content": "Here is the current reporting on the U.S. bombing in Iran.",
            "agent_id": "primary",
        },
    )()

    response = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "tell me about the current iran bombings by the usa, search the web or load news sources and let me know"},
        headers={"X-HG-Timezone": "America/St_Johns"},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["search"]["kind"] == "news"
    assert "iran" in data["search"]["query"].lower()
    assert "newfoundland and labrador" not in data["search"]["query"].lower()
    assert data["search"]["plan_template"] == "planned_research_summary_v1"


@patch("hg_gateway.routes._geocode_place")
def test_resolve_weather_region_prefers_requested_place_over_local_default(mock_geocode):
    mock_geocode.return_value = {
        "place_name": "Paris",
        "place_label": "Paris, Ile-de-France, France",
        "region_name": "Ile-de-France",
        "country": "France",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "timezone": "Europe/Paris",
        "is_default": False,
    }

    region = gateway_routes._resolve_weather_region(None, "What is the weather in Paris right now?")

    assert region["place_name"] == "Paris"
    assert region["place_label"] == "Paris, Ile-de-France, France"
    assert float(region["latitude"]) == pytest.approx(48.8566)
    assert float(region["longitude"]) == pytest.approx(2.3522)


def test_infer_local_region_does_not_treat_plain_on_as_ontario():
    region = gateway_routes._infer_local_region(None, "tell me what is going on with the latest Iran bombing reports")
    assert region["province_code"] == "NL"


def test_plan_research_request_uses_planner_for_current_events_prompt():
    planned = gateway_routes._plan_research_request(
        "what's going on today with the us government and flock cameras everywhere?",
        None,
    )
    assert planned is not None
    assert planned["kind"] == "news"
    assert planned["plan"]["template"] == "planned_research_summary_v1"
    assert planned["plan"]["dag"]["inputs"]["freshness"] == "pw"
    assert planned["plan"]["dag"]["inputs"]["fetch_page_count"] >= 4
    assert "newfoundland" not in planned["query"].lower()
