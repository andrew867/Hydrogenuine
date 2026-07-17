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
    TestClient = None
    app = None


def _headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    if TestClient is None:
        pytest.skip("operator_console/server not found")
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", str(tmp_path / "gateway.sqlite3"))
    monkeypatch.setenv("HG_ENV", "test")
    return TestClient(app)


def test_manual_scheduled_job_run_is_blocked_without_gate(monkeypatch, client):
    monkeypatch.setattr("app.api.workflows._workspace_root", lambda: Path("."))
    monkeypatch.setattr(
        "app.api.workflows.list_scheduled_jobs",
        lambda root: [{"job_id": "social", "workflow_id": "social", "inputs": {}, "agency_control": {}}],
    )
    monkeypatch.setattr(
        "app.api.workflows.read_scheduled_dag",
        lambda root, job_id: {"dag": {"workflow_id": job_id, "nodes": []}},
    )

    response = client.post("/api/v1/workflows/scheduled-jobs/social/run", headers=_headers())
    assert response.status_code == 423, response.text


def test_manual_scheduled_job_run_allowed_with_gate(monkeypatch, client):
    monkeypatch.setattr("app.api.workflows._workspace_root", lambda: Path("."))
    monkeypatch.setattr(
        "app.api.workflows.list_scheduled_jobs",
        lambda root: [{"job_id": "social", "workflow_id": "social", "inputs": {}, "agency_control": {}}],
    )
    monkeypatch.setattr(
        "app.api.workflows.read_scheduled_dag",
        lambda root, job_id: {"dag": {"workflow_id": job_id, "nodes": []}},
    )
    monkeypatch.setattr(
        "app.api.workflows.submit_run",
        lambda dag: {"ok": True, "run_id": "run-1", "status": "completed"},
    )

    create_policy = client.post(
        "/api/v1/governance/gate/benchmark-sets",
        headers=_headers(),
        json={"workflow_family": "social", "title": "Gate", "description": "Test", "weights": {"p_h": 0.3, "p_ai": 0.2, "p_h_odei": 0.5}},
    )
    benchmark_set_id = create_policy.json()["benchmark_set_id"]
    benchmark_run = client.post(
        "/api/v1/governance/gate/benchmark-runs",
        headers=_headers(),
        json={"benchmark_set_id": benchmark_set_id, "workflow_family": "social", "candidate_label": "v1", "observations": {"p_h": 0.7, "p_ai": 0.5, "p_h_odei": 0.8}},
    )
    evaluation = client.post(
        "/api/v1/governance/gate/evaluate",
        headers=_headers(),
        json={"benchmark_run_id": benchmark_run.json()["benchmark_run_id"]},
    )
    client.post(
        "/api/v1/governance/gate/release-verdicts",
        headers=_headers(),
        json={"workflow_family": "social", "target_kind": "workflow", "target_id": "social", "evaluation_id": evaluation.json()["evaluation_id"], "verdict": "eligible", "reason": "ready"},
    )

    response = client.post("/api/v1/workflows/scheduled-jobs/social/run", headers=_headers())
    assert response.status_code == 200, response.text
