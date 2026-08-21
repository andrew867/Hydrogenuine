from __future__ import annotations

from fastapi.testclient import TestClient


def _app(monkeypatch, tmp_path, *, auth_mode: str, store: str = "memory"):
    monkeypatch.setenv("HG_GATEWAY_AUTH_MODE", auth_mode)
    monkeypatch.setenv("HG_ENV", "Demo")
    monkeypatch.setenv("HG_GATEWAY_STORE", store)
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    monkeypatch.setenv("HG_COMMUNITY_DATA_DIR", str(tmp_path / "community"))
    from hg_gateway.main import app
    from hg_gateway.store import reset_store_for_tests

    reset_store_for_tests()
    return app


def test_local_demo_accepts_no_key_and_ignores_stale_browser_token(monkeypatch, tmp_path):
    client = TestClient(_app(monkeypatch, tmp_path, auth_mode="local-no-key"))
    assert client.get("/v1/chats").status_code == 200
    assert client.get("/v1/chats", headers={"x-api-key": "stale-browser-value"}).status_code == 200
    health = client.get("/healthz").json()
    assert health["auth_mode"] == "local-no-key"


def test_api_key_mode_explains_local_transport_credential(monkeypatch, tmp_path):
    monkeypatch.setenv("HG_GATEWAY_API_KEY", "expected-local-transport")
    client = TestClient(_app(monkeypatch, tmp_path, auth_mode="api-key"))
    response = client.get("/v1/chats", headers={"x-api-key": "wrong"})
    assert response.status_code == 401
    detail = response.json()["detail"]
    assert "Invalid API key" not in detail
    assert "local HTTP gateway" in detail
    assert "not a model-provider API key" in detail


def test_sqlite_chat_store_survives_gateway_store_recreation(monkeypatch, tmp_path):
    app = _app(monkeypatch, tmp_path, auth_mode="local-no-key", store="sqlite")
    client = TestClient(app)
    first = client.post("/v1/chats", json={"title": "First session"})
    second = client.post("/v1/chats", json={"title": "Second session"})
    assert first.status_code == 200
    assert second.status_code == 200

    from hg_gateway.store import reset_store_for_tests

    reset_store_for_tests()
    resumed = TestClient(app).get("/v1/chats")
    assert resumed.status_code == 200
    titles = {chat["title"] for chat in resumed.json()["chats"]}
    assert titles >= {"First session", "Second session"}
