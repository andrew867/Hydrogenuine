"""API tests for Hydrogenuine Operator Console (Phase 1)."""

import os
import sys
from pathlib import Path

import pytest

# Import app from operator_console/server (conftest sets HG_* env before collection)
_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
    _client_fixture = lambda: TestClient(app)
else:
    app = None
    _client_fixture = None


def _api_headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    """TestClient for operator_console API (uses env from conftest)."""
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


@pytest.fixture
def valid_dag():
    """Minimal valid DAG for validate/review/run."""
    return {
        "graph_id": "example_ui_v1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1},
        "inputs": {"x": 1},
        "nodes": [
            {
                "id": "noop",
                "type": "eval",
                "assigned_entity": "evaluator",
                "depends_on": [],
                "inputs": {"expression": 1, "outputs": ["x"]},
            }
        ],
    }


def test_healthz(client):
    """GET /healthz returns ok."""
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_runs_list_requires_auth(client):
    """GET /api/v1/runs without auth returns 401 or 403."""
    r = client.get("/api/v1/runs")
    assert r.status_code in (401, 403)


def test_runs_list(client):
    """GET /api/v1/runs returns list with auth."""
    r = client.get("/api/v1/runs", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "runs" in data
    assert isinstance(data["runs"], list)


def test_runs_detail_not_found(client):
    """GET /api/v1/runs/{id} for unknown run returns error."""
    r = client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is False
    assert data.get("error", {}).get("code") == "NOT_FOUND"


def test_graphs_validate(client, valid_dag):
    """POST /api/v1/graphs/validate with valid DAG returns expected shape."""
    r = client.post("/api/v1/graphs/validate", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert "ok" in data
    assert "errors" in data
    assert "warnings" in data


def test_graphs_review(client, valid_dag):
    """POST /api/v1/graphs/review with valid DAG returns ok, reviewed_dag, report."""
    r = client.post("/api/v1/graphs/review", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "reviewed_dag" in data
    assert "report" in data
    assert "blocked" in data["report"]
    assert "issues" in data["report"]


def test_graphs_run(client, valid_dag):
    """POST /api/v1/graphs/run with valid DAG returns ok, run_id, status."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "run_id" in data
    assert "status" in data


def test_run_detail_after_submit(client, valid_dag):
    """Submit run then GET run detail returns summary and graph when present."""
    run_r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert run_r.status_code == 200
    run_data = run_r.json()
    assert run_data.get("ok") is True
    run_id = run_data["run_id"]
    detail_r = client.get(f"/api/v1/runs/{run_id}", headers=_api_headers())
    assert detail_r.status_code == 200
    detail = detail_r.json()
    assert detail.get("ok") is True
    assert detail.get("run_id") == run_id
    # Stub worker writes summary.json and graph.json
    assert "summary" in detail
    assert "graph" in detail
    assert "lineage_summary" in detail
    assert detail["lineage_summary"]["run_id"] == run_id


def test_run_lineage_endpoint_after_submit(client, valid_dag):
    """Submit run then GET run lineage returns a navigable lineage summary."""
    run_r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert run_r.status_code == 200
    run_data = run_r.json()
    assert run_data.get("ok") is True
    run_id = run_data["run_id"]
    lineage_r = client.get(f"/api/v1/runs/{run_id}/lineage", headers=_api_headers())
    assert lineage_r.status_code == 200
    lineage = lineage_r.json()
    assert lineage.get("run_id") == run_id
    assert lineage.get("workflow_id") == "example_ui_v1"
    assert "lineage_graph" in lineage
    assert "nodes" in lineage["lineage_graph"]
    assert "edges" in lineage["lineage_graph"]


def test_events_stream_token_endpoint(client, valid_dag):
    """GET /api/v1/runs/{id}/events/stream-token mints a short-lived SSE token."""
    from app.services import stream_tokens

    run_r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert run_r.status_code == 200
    run_id = run_r.json()["run_id"]
    token_r = client.get(f"/api/v1/runs/{run_id}/events/stream-token", headers=_api_headers())
    assert token_r.status_code == 200
    body = token_r.json()
    assert "token" in body
    assert body.get("expires_in_sec") == 120
    assert stream_tokens.validate_stream_token(body["token"], run_id) is True


def test_run_swarm_tree_endpoint_after_submit(client, valid_dag):
    """Submit run then GET run swarm returns the lineage-compatible swarm tree shape."""
    run_r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert run_r.status_code == 200
    run_data = run_r.json()
    assert run_data.get("ok") is True
    run_id = run_data["run_id"]
    swarm_r = client.get(f"/api/v1/runs/{run_id}/swarm", headers=_api_headers())
    assert swarm_r.status_code == 200
    swarm = swarm_r.json()
    assert swarm.get("run_id") == run_id
    assert "swarm_tree" in swarm
    assert "lineage_graph" in swarm
