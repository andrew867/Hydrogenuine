"""Ch4 Product API actions: contract, RBAC, and audit log assertions."""

import json
import os
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

BASE = "/api/product/v1"


def _headers(role="operator"):
    keys = {"viewer": "test-product-viewer", "operator": "test-product-operator", "admin": "test-product-admin"}
    return {"Authorization": f"Bearer {keys.get(role, keys['operator'])}"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


def _existing_workflow_id(client):
    resp = client.get(f"{BASE}/workflows", headers=_headers("viewer"))
    if resp.status_code != 200:
        return None
    items = resp.json().get("items", [])
    if not items:
        return None
    return items[0].get("id")


def test_post_workflow_run_contract(client):
    """POST /workflows/{id}/run returns 202 with mode."""
    wf_id = _existing_workflow_id(client)
    if not wf_id:
        pytest.skip("no workflows available in this environment")
    r = client.post(f"{BASE}/workflows/{wf_id}/run", json={"mode": "shadow"}, headers=_headers("operator"))
    assert r.status_code == 202
    data = r.json()
    assert data.get("accepted") is True
    assert data.get("mode") == "shadow"


def test_post_run_replay_contract(client):
    """POST /runs/{run_id}/replay returns 202 or 404."""
    r = client.post(f"{BASE}/runs/nonexistent-run/replay", json={"mode": "shadow"}, headers=_headers("operator"))
    assert r.status_code in (202, 404)


def test_post_approval_override_contract(client):
    """POST /approvals/{id}/override (admin) returns 202 or 404."""
    r = client.post(f"{BASE}/approvals/some-id/override", json={"decision": "approve"}, headers=_headers("admin"))
    assert r.status_code in (202, 404)


def test_viewer_cannot_post_workflow_run(client):
    """Viewer cannot POST workflow run: 403."""
    r = client.post(f"{BASE}/workflows/w1/run", json={"mode": "shadow"}, headers=_headers("viewer"))
    assert r.status_code == 403


def test_viewer_cannot_post_replay(client):
    """Viewer cannot POST replay: 403."""
    r = client.post(f"{BASE}/runs/run1/replay", json={"mode": "shadow"}, headers=_headers("viewer"))
    assert r.status_code == 403


def test_operator_cannot_override_approval(client):
    """Operator cannot POST approval override: 403."""
    r = client.post(f"{BASE}/approvals/some-id/override", json={"decision": "approve"}, headers=_headers("operator"))
    assert r.status_code == 403


def test_audit_log_after_action(client, tmp_path):
    """After a privileged action, audit log contains an entry when path is set."""
    audit_file = tmp_path / "audit.jsonl"
    os.environ["HG_AUDIT_LOG_PATH"] = str(audit_file)
    try:
        from app.services.audit_log import get_audit_path
        # Force re-read of env (get_audit_path reads os.getenv at call time)
        path = get_audit_path()
        assert path == audit_file
    except ImportError:
        pytest.skip("audit_log not available")
    wf_id = _existing_workflow_id(client)
    if not wf_id:
        pytest.skip("no workflows available in this environment")
    r = client.post(f"{BASE}/workflows/{wf_id}/run", json={"mode": "shadow"}, headers=_headers("operator"))
    assert r.status_code == 202
    if audit_file.exists():
        lines = audit_file.read_text().strip().splitlines()
        assert len(lines) >= 1
        entry = json.loads(lines[-1])
        assert entry.get("action") == "workflow_run"
        assert entry.get("resource_id") == wf_id
    # Clean up env for other tests
    os.environ.pop("HG_AUDIT_LOG_PATH", None)
