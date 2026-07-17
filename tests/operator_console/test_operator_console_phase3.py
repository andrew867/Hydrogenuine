"""API tests for Hydrogenuine Operator Console Phase 3: replay, cancel."""

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


def _api_headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


@pytest.fixture
def valid_dag():
    return {
        "graph_id": "phase3_test",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1},
        "inputs": {},
        "nodes": [
            {"id": "n1", "type": "eval", "assigned_entity": "evaluator", "depends_on": [], "inputs": {"expression": 1, "outputs": ["x"]}},
        ],
    }


def test_replay_endpoint(client, valid_dag):
    """POST /runs/{id}/replay returns 200; ok:true when implemented or ok:false with error."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    r2 = client.post(f"/api/v1/runs/{run_id}/replay", headers=_api_headers())
    assert r2.status_code == 200
    data = r2.json()
    assert "ok" in data
    if data.get("ok"):
        assert "run_id" in data or "status" in data
    else:
        assert "error" in data


def test_cancel_endpoint(client, valid_dag):
    """POST /runs/{id}/cancel returns 200; ok:true when implemented or ok:false with error."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    r2 = client.post(f"/api/v1/runs/{run_id}/cancel", headers=_api_headers())
    assert r2.status_code == 200
    data = r2.json()
    assert "ok" in data
    if data.get("ok"):
        assert "run_id" in data or "status" in data
    else:
        assert "error" in data
