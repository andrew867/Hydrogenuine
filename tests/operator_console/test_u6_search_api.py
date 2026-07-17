"""U6: unified search and explain-block operator API tests."""

import sys
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
else:
    app = None


def _headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    if app is None:
        pytest.skip("operator_console/server not found")
    return TestClient(app)


def test_search_requires_auth(client):
    r = client.get("/api/v1/search")
    assert r.status_code in (401, 403)


def test_search_returns_items(client):
    r = client.get("/api/v1/search?q=&limit=5", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert isinstance(data.get("items"), list)


def test_search_run_filter(client):
    r = client.get("/api/v1/search?q=example&limit=10", headers=_headers())
    assert r.status_code == 200
    items = r.json().get("items") or []
    for item in items:
        assert "type" in item
        assert "href" in item


def test_explain_block_requires_ref(client):
    r = client.get("/api/v1/operator/explain-block", headers=_headers())
    assert r.status_code == 400


def test_explain_block_unknown_work_item(client):
    r = client.get(
        "/api/v1/operator/explain-block?work_item_id=nonexistent-wi-u6",
        headers=_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("ref_id") == "nonexistent-wi-u6"
    assert "blocked" in data
