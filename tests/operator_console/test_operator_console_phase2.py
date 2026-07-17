"""API tests for Hydrogenuine Operator Console Phase 2: snapshots, checkpoints, SSE."""

import json
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
        "graph_id": "api_state_test",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1},
        "inputs": {},
        "nodes": [
            {"id": "n1", "type": "eval", "assigned_entity": "evaluator", "depends_on": [], "inputs": {"expression": 1, "outputs": ["x"]}},
        ],
    }


def test_snapshots_list(client, valid_dag):
    """GET /runs/{id}/snapshots returns ok and snapshots list (empty when no state_history)."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    r2 = client.get(f"/api/v1/runs/{run_id}/snapshots", headers=_api_headers())
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("ok") is True
    assert data.get("run_id") == run_id
    assert "snapshots" in data
    assert isinstance(data["snapshots"], list)


def test_snapshots_get(client, valid_dag):
    """GET /runs/{id}/snapshots/{seq} returns 404 when sequence is not present."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    r2 = client.get(f"/api/v1/runs/{run_id}/snapshots/0", headers=_api_headers())
    assert r2.status_code == 404


def test_fork_from_snapshot(client, valid_dag):
    """POST /runs/{id}/fork/{seq} returns run_id for valid snapshot sequence."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    r2 = client.post(f"/api/v1/runs/{run_id}/fork/1", headers=_api_headers())
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("ok") is True
    assert "run_id" in data


def test_checkpoints_list(client, valid_dag):
    """GET /runs/{id}/checkpoints returns ok and checkpoints list (empty when none)."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    r2 = client.get(f"/api/v1/runs/{run_id}/checkpoints", headers=_api_headers())
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("ok") is True
    assert data.get("run_id") == run_id
    assert "checkpoints" in data
    assert isinstance(data["checkpoints"], list)


def test_checkpoints_list_with_data(client, valid_dag):
    """GET /runs/{id}/checkpoints returns list with items when run_dir has checkpoints.json."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    from app.services.run_index_db import get_run
    run_row = get_run(run_id)
    assert run_row is not None
    run_dir = Path(run_row["run_dir"])
    (run_dir / "checkpoints.json").write_text(
        json.dumps({"checkpoints": [{"checkpoint_id": "cp1", "status": "pending", "node_id": "n1", "created_at": "2025-01-01T00:00:00Z"}]}),
        encoding="utf-8",
    )
    r2 = client.get(f"/api/v1/runs/{run_id}/checkpoints", headers=_api_headers())
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("ok") is True
    assert len(data["checkpoints"]) == 1
    assert data["checkpoints"][0]["checkpoint_id"] == "cp1"
    assert data["checkpoints"][0]["status"] == "pending"


def test_checkpoints_approve(client, valid_dag):
    """POST /runs/{id}/checkpoints/{cp_id}/approve returns 200 and ok: true."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    r2 = client.post(
        f"/api/v1/runs/{run_id}/checkpoints/cp1/approve",
        json={"comment": "ok"},
        headers=_api_headers(),
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("ok") is True


def test_checkpoints_deny(client, valid_dag):
    """POST /runs/{id}/checkpoints/{cp_id}/deny returns 200 and ok: true."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    r2 = client.post(
        f"/api/v1/runs/{run_id}/checkpoints/cp2/deny",
        json={"comment": "rejected"},
        headers=_api_headers(),
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("ok") is True


def test_events_stream_not_found_404(client):
    """GET /runs/{id}/events/stream for unknown run returns 404."""
    r = client.get(
        "/api/v1/runs/00000000-0000-0000-0000-000000000000/events/stream",
        headers=_api_headers(),
    )
    assert r.status_code == 404


def test_events_stream_returns_sse(client, valid_dag):
    """GET /runs/{id}/events/stream returns SSE stream; first event is ready; content-type correct."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    r2 = client.get(f"/api/v1/runs/{run_id}/events/stream", headers=_api_headers())
    assert r2.status_code == 200
    assert "text/event-stream" in r2.headers.get("content-type", "")
    # Spec: first event is event: ready with data: {}
    text = r2.text
    assert "event: ready" in text
    assert "data: {}" in text


# --- Phase 4: state and JSON artifact ---


def test_run_state_missing(client, valid_dag):
    """GET /runs/{id}/state returns ok: false with MISSING when state.json not present."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    from app.services.run_index_db import get_run
    run_row = get_run(run_id)
    if run_row:
        state_path = Path(run_row["run_dir"]) / "state.json"
        if state_path.exists():
            state_path.unlink()
    r2 = client.get(f"/api/v1/runs/{run_id}/state", headers=_api_headers())
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("ok") is False
    assert data.get("error", {}).get("code") == "MISSING"


def test_run_state_present(client, valid_dag):
    """GET /runs/{id}/state returns ok: true and state when state.json exists."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    from app.services.run_index_db import get_run
    run_row = get_run(run_id)
    assert run_row is not None
    run_dir = Path(run_row["run_dir"])
    (run_dir / "state.json").write_text(
        json.dumps({"nodes": [{"id": "n1", "status": "succeeded"}], "final_status": "completed"}),
        encoding="utf-8",
    )
    r2 = client.get(f"/api/v1/runs/{run_id}/state", headers=_api_headers())
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("ok") is True
    assert "state" in data
    assert data["state"].get("final_status") == "completed"


def test_run_state_not_found(client):
    """GET /runs/{id}/state for unknown run returns ok: false NOT_FOUND."""
    r = client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000/state", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is False
    assert data.get("error", {}).get("code") == "NOT_FOUND"


def test_artifact_json_missing(client, valid_dag):
    """GET /runs/{id}/artifacts/json/{name} returns ok: false when artifact not found."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    r2 = client.get(f"/api/v1/runs/{run_id}/artifacts/json/memory", headers=_api_headers())
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("ok") is False
    assert data.get("error", {}).get("code") == "MISSING"


def test_artifact_json_present(client, valid_dag):
    """GET /runs/{id}/artifacts/json/{name} returns ok: true and data when artifact exists."""
    r = client.post("/api/v1/graphs/run", json={"dag": valid_dag}, headers=_api_headers())
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    from app.services.run_index_db import get_run
    run_row = get_run(run_id)
    run_dir = Path(run_row["run_dir"])
    (run_dir / "memory.json").write_text(json.dumps({"items": ["a", "b"]}), encoding="utf-8")
    r2 = client.get(f"/api/v1/runs/{run_id}/artifacts/json/memory", headers=_api_headers())
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("ok") is True
    assert data.get("data") == {"items": ["a", "b"]}
