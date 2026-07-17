import os

import pytest
from fastapi.testclient import TestClient

from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway.main import app
from hg_gateway import routes as routes_module
from hg_gateway import store as store_module
from hg_gateway.store import get_store


def _install_mock_registry(monkeypatch, response_text: str = "A concise swarm reply.") -> None:
    async def mock_stream(*, messages, **kwargs):
        yield response_text

    class MockRegistry:
        def stream_complete(self, *args, **kwargs):
            return mock_stream(*args, **kwargs)

    import hg_llm

    monkeypatch.setattr(hg_llm, "get_default_registry", lambda: MockRegistry())


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


def test_swarm_run_records_relationship_modulation(monkeypatch, client):
    _install_mock_registry(monkeypatch, response_text="Swarm member response.")
    monkeypatch.setattr(routes_module, "_requires_approval", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        routes_module,
        "_get_swarm_personas",
        lambda count: [
            {"fingerprint_id": "ada_lovelace", "skin_id": None},
            {"fingerprint_id": "nikola_tesla", "skin_id": None},
        ][:count],
    )

    response = client.post("/v1/swarm/run", json={"task": "Say hello in one sentence.", "count": 2})

    assert response.status_code == 200, response.text
    payload = response.json()
    store = get_store()
    rows = store.persona_autonomy_list("default", swarm_run_id=payload["swarm_run_id"], limit=10)
    assert len(rows) == 2
    assert any(row.get("relationship_type") == "respect" for row in rows)

    workspace = client.get(f"/v1/swarms/{payload['swarm_run_id']}")
    assert workspace.status_code == 200, workspace.text
    body = workspace.json()
    assert body["naturalness"]["summary"]["total_turns"] == 2
    assert body["autonomy"]["summary"]["total_turns"] == 2
