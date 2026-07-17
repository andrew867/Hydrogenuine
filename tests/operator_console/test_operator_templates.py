"""Operator UI template and tool trace endpoints."""

import sys
from pathlib import Path

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

BASE = "/api/v1"


def _headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


def test_templates_list(client):
    r = client.get(f"{BASE}/templates", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert isinstance(data.get("templates"), list)


def test_tool_trace_not_found(client):
    r = client.get(f"{BASE}/runs/not-a-run/tool-trace", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is False
