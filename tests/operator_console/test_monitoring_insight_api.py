"""Tests for /api/v1/status/insight monitoring summary endpoint."""

import json
import sys
import time
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.run_index_db import upsert_run
    _client_fixture = lambda: TestClient(app)
else:
    _client_fixture = None
    upsert_run = None


def _api_headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


def _write_summary(run_dir: Path, final_status: str, blocked: int = 0, errors: list | None = None):
    payload = {
        "final_status": final_status,
        "counts": {"blocked": blocked},
        "error_summary": errors or [],
    }
    (run_dir / "summary.json").write_text(json.dumps(payload), encoding="utf-8")


def test_status_insight_requires_auth(client):
    r = client.get("/api/v1/status/insight")
    assert r.status_code in (401, 403)


def test_status_insight_empty_contract(client):
    r = client.get("/api/v1/status/insight?hours=24&limit_runs=10", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("window_hours") == 24
    assert isinstance(data.get("totals"), dict)
    assert isinstance(data.get("dag_runtime"), dict)
    assert isinstance(data.get("by_workflow"), list)
    assert isinstance(data.get("anomalies"), list)
    assert isinstance(data.get("recent_runs"), list)


def test_status_insight_detects_outlier_and_policy_violation(client, tmp_path):
    now = time.time()

    run_a = tmp_path / "run-a"
    run_a.mkdir()
    _write_summary(run_a, "completed")
    upsert_run(
        {
            "run_id": "run-a",
            "graph_id": "wf-insight",
            "status": "completed",
            "started_at": now - 120,
            "ended_at": now - 110,  # 10s
            "run_dir": str(run_a),
        }
    )

    run_b = tmp_path / "run-b"
    run_b.mkdir()
    _write_summary(run_b, "completed")
    upsert_run(
        {
            "run_id": "run-b",
            "graph_id": "wf-insight",
            "status": "completed",
            "started_at": now - 240,
            "ended_at": now - 228,  # 12s
            "run_dir": str(run_b),
        }
    )

    run_c = tmp_path / "run-c"
    run_c.mkdir()
    _write_summary(
        run_c,
        "failed",
        blocked=1,
        errors=[{"node_id": "n1", "code": "STEERING_BLOCKED", "failure_class": "safety_blocked"}],
    )
    upsert_run(
        {
            "run_id": "run-c",
            "graph_id": "wf-insight",
            "status": "failed",
            "started_at": now - 360,
            "ended_at": now - 240,  # 120s outlier
            "run_dir": str(run_c),
        }
    )

    r = client.get("/api/v1/status/insight?hours=24&limit_runs=200", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True

    totals = data["totals"]
    assert totals["runs"] >= 3
    assert totals["failed_runs"] >= 1
    assert totals["blocked_nodes"] >= 1
    assert totals["policy_violations"] >= 1

    wf = next((w for w in data["by_workflow"] if w["workflow_id"] == "wf-insight"), None)
    assert wf is not None
    assert wf["runs"] >= 3
    assert wf["failed_runs"] >= 1
    assert wf["policy_violations"] >= 1

    anomaly_types = {a["type"] for a in data["anomalies"]}
    assert "duration_outlier" in anomaly_types
    assert "policy_violation" in anomaly_types

    r2 = client.get("/api/v1/status/insight?hours=24&limit_runs=200&dag_only=true", headers=_api_headers())
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2.get("ok") is True
    assert d2.get("dag_only") is True
