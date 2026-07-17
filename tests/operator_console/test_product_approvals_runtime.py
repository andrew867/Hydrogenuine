"""Product approvals should be sourced from the gateway runtime store, not memory summaries."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
    _client_fixture = lambda: TestClient(app)
else:
    _client_fixture = None

BASE = "/api/product/v1"


def _headers(role: str = "viewer"):
    keys = {"viewer": "test-product-viewer", "operator": "test-product-operator", "admin": "test-product-admin"}
    return {"Authorization": f"Bearer {keys.get(role, keys['viewer'])}"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


def test_product_approvals_use_gateway_runtime_store(client, monkeypatch):
    import hg_gateway.store as store_module

    db_dir = Path(".codex_tmp") / "product-approvals-runtime"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = (db_dir / f"product-approvals-{uuid4().hex}.sqlite3").resolve()
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(db_path))
    monkeypatch.setenv("HG_PRODUCT_TENANT_ID", "product-runtime")
    store_module._store = None
    try:
        store = store_module.get_store()
        approval_id = store.approval_add(
            "product-runtime",
            kind="tool_use",
            title="Approve outbound write",
            summary="Live runtime approval pending",
            risk="high",
            requested_by="agent-runtime",
            payload={"graph_id": "wf-weather", "note": "safe"},
            chat_id="chat-runtime",
        )

        r = client.get(f"{BASE}/approvals", headers=_headers("viewer"))
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["id"] == approval_id
        assert item["status"] == "pending"
        assert item["decision"] == "pending"
        assert item["kind"] == "tool_use"
        assert item["requestedBy"] == "agent-runtime"
        assert item["workflow"] == "wf-weather"
        assert item["origin"]["chat_id"] == "chat-runtime"
        assert item["origin"]["workflow_id"] == "wf-weather"

        detail = client.get(f"{BASE}/approvals/{approval_id}", headers=_headers("viewer"))
        assert detail.status_code == 200
        detail_data = detail.json()
        assert detail_data["id"] == approval_id
        assert detail_data["status"] == "pending"
        assert detail_data["summary"] == "Live runtime approval pending"
        assert detail_data["chat_id"] == "chat-runtime"
    finally:
        store_module._store = None
