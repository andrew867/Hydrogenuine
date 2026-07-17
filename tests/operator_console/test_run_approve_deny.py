"""Tests for run-level gate approval: GET run detail (blocked/pending_approval), POST approve, POST deny."""

import json
import os
import tempfile
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    import sys
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from operator_console.server.app.main import app
else:
    app = None


def _api_headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client_and_pending_run(monkeypatch):
    """Operator console client and a run_id with status pending_approval in gateway DB."""
    if app is None:
        pytest.skip("operator_console/server not found")
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    monkeypatch.setenv("HG_GATEWAY_STORE", "sqlite")
    monkeypatch.setenv("HG_GATEWAY_DB_PATH", path)
    try:
        from hg_gateway.db import get_connection
        with get_connection() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY, graph_id TEXT, status TEXT, started_at REAL, ended_at REAL,
                run_dir TEXT, correlation_id TEXT, blocked_reason TEXT, pending_request_json TEXT)"""
            )
            c.execute(
                "INSERT INTO runs (run_id, graph_id, status, started_at, ended_at, run_dir, correlation_id, blocked_reason, pending_request_json) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    "run-pending-test-1",
                    "test-workflow",
                    "pending_approval",
                    1773086300.0,
                    None,
                    None,
                    "corr-pending-1",
                    "blocked by release gate",
                    json.dumps({"workflow_id": "test-workflow", "tenant_id": "default", "actor_id": "api", "correlation_id": "corr-pending-1", "resolved_inputs": {}, "dedup_key": None}),
                ),
            )
        # Ensure operator_console uses this DB
        from operator_console.server.app.services import run_index_db
        monkeypatch.setenv("HG_GATEWAY_DB_PATH", path)
        client = TestClient(app)
        yield client, "run-pending-test-1", path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_get_run_pending_approval_returns_run_dir_missing(client_and_pending_run):
    """GET /runs/{id} for a pending_approval run returns ok, run_dir_missing, status, blocked_reason."""
    client, run_id, _ = client_and_pending_run
    from hg_gateway.db import get_connection
    with get_connection() as c:
        c.execute("UPDATE runs SET status = ? WHERE run_id = ?", ("pending_approval", run_id))
    r = client.get(f"/api/v1/runs/{run_id}", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("run_id") == run_id
    assert data.get("status") == "pending_approval"
    assert data.get("run_dir_missing") is True
    assert data.get("blocked_reason") is not None


def test_approve_run_pending_approval(client_and_pending_run):
    """POST /runs/{id}/approve for pending_approval run returns 200 and ok."""
    client, run_id, _ = client_and_pending_run
    from hg_gateway.db import get_connection
    with get_connection() as c:
        c.execute("UPDATE runs SET status = ? WHERE run_id = ?", ("pending_approval", run_id))
    r = client.post(f"/api/v1/runs/{run_id}/approve", headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("run_id") == run_id
    with get_connection() as c:
        row = c.execute("SELECT status FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    assert row is not None
    assert row[0] == "approved_pending_launch"


def test_deny_run_pending_approval(client_and_pending_run):
    """POST /runs/{id}/deny for pending_approval run returns 200 and marks run blocked."""
    client, run_id, _ = client_and_pending_run
    from hg_gateway.db import get_connection
    with get_connection() as c:
        c.execute("UPDATE runs SET status = ? WHERE run_id = ?", ("pending_approval", run_id))
    r = client.post(f"/api/v1/runs/{run_id}/deny", json={"reason": "denied by test"}, headers=_api_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    with get_connection() as c:
        row = c.execute("SELECT status, blocked_reason FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    assert row is not None
    assert row[0] == "blocked"
    assert "denied" in (row[1] or "")


def test_approve_run_not_pending_returns_400(client_and_pending_run):
    """POST /runs/{id}/approve for run that is not pending_approval returns 400."""
    client, run_id, _ = client_and_pending_run
    from hg_gateway.db import get_connection
    with get_connection() as c:
        c.execute("UPDATE runs SET status = ? WHERE run_id = ?", ("running", run_id))
    r = client.post(f"/api/v1/runs/{run_id}/approve", headers=_api_headers())
    assert r.status_code == 400
    assert r.json().get("detail", {}).get("code") == "INVALID_STATE"
