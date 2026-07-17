"""Ch4 Product API: contract, RBAC, and redaction tests.

Product API is mounted at /api/product/v1. Auth via Bearer token; role is
derived from key (viewer / operator / admin) for RBAC.
"""

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
    app = None
    _client_fixture = None

BASE = "/api/product/v1"

# Role-based keys (set in conftest or env); tests assume these are configured
def _headers(role: str):
    """Return Authorization header for role (viewer, operator, admin)."""
    keys = {
        "viewer": "test-product-viewer",
        "operator": "test-product-operator",
        "admin": "test-product-admin",
    }
    key = keys.get(role, "test-product-operator")
    return {"Authorization": f"Bearer {key}"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


# ----- Contract: read-only endpoints -----


def test_product_health_contract(client):
    """GET /api/product/v1/health returns 200 and ok/status."""
    r = client.get(f"{BASE}/health")
    assert r.status_code == 200
    data = r.json()
    assert "ok" in data
    assert data.get("ok") is True


def test_product_workflows_list_contract(client):
    """GET /api/product/v1/workflows returns 200, items array, total."""
    r = client.get(f"{BASE}/workflows", headers=_headers("viewer"))
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert "total" in data
    assert isinstance(data["total"], int)


def test_product_workflows_list_pagination(client):
    """GET /api/product/v1/workflows accepts limit and offset."""
    r = client.get(f"{BASE}/workflows", params={"limit": 5, "offset": 0}, headers=_headers("viewer"))
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert len(data["items"]) <= 5


def test_product_workflow_detail_contract(client):
    """GET /api/product/v1/workflows/{id} returns 200 with workflow fields or 404."""
    r = client.get(f"{BASE}/workflows/nonexistent-id", headers=_headers("viewer"))
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        data = r.json()
        assert "id" in data
        assert "name" in data or "status" in data


def test_product_runs_list_contract(client):
    """GET /api/product/v1/runs returns 200, items, total."""
    r = client.get(f"{BASE}/runs", headers=_headers("viewer"))
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert "total" in data


def test_product_runs_list_filtering(client):
    """GET /api/product/v1/runs accepts workflow_id and status query params."""
    r = client.get(f"{BASE}/runs", params={"workflow_id": "w1", "status": "completed"}, headers=_headers("viewer"))
    assert r.status_code == 200
    data = r.json()
    assert "items" in data


def test_product_run_detail_contract(client):
    """GET /api/product/v1/runs/{run_id} returns 200 with run fields or 404."""
    r = client.get(f"{BASE}/runs/00000000-0000-0000-0000-000000000000", headers=_headers("viewer"))
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        data = r.json()
        assert "run_id" in data
        assert "status" in data


def test_product_run_artifacts_contract(client):
    """GET /api/product/v1/runs/{run_id}/artifacts returns 200, items (metadata only)."""
    r = client.get(f"{BASE}/runs/00000000-0000-0000-0000-000000000000/artifacts", headers=_headers("viewer"))
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        data = r.json()
        assert "items" in data
        for item in data.get("items", []):
            assert "name" in item or "kind" in item


def test_product_incident_replay_not_found(client):
    """POST /api/product/v1/incidents/{id}/replay returns 404 for unknown incident."""
    r = client.post(
        f"{BASE}/incidents/00000000-0000-0000-0000-000000000000/replay",
        json={"shadow": True},
        headers=_headers("operator"),
    )
    assert r.status_code == 404


def test_product_approvals_list_contract(client):
    """GET /api/product/v1/approvals returns 200, items, total."""
    r = client.get(f"{BASE}/approvals", headers=_headers("viewer"))
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data


def test_product_incidents_list_contract(client):
    """GET /api/product/v1/incidents returns 200, items, total."""
    r = client.get(f"{BASE}/incidents", headers=_headers("viewer"))
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data


def test_product_policies_blacklist_contract(client):
    """GET /api/product/v1/policies/blacklist returns 200."""
    r = client.get(f"{BASE}/policies/blacklist", headers=_headers("viewer"))
    assert r.status_code == 200


def test_product_metrics_summary_contract(client):
    """GET /api/product/v1/metrics/summary returns 200 with period/cost/sla."""
    r = client.get(f"{BASE}/metrics/summary", headers=_headers("viewer"))
    assert r.status_code == 200
    data = r.json()
    assert "period" in data or "cost" in data or "sla" in data
    assert "pdf_dashboard" in data


def test_product_metrics_reports_contract(client):
    """GET /api/product/v1/metrics/reports returns report listing shape."""
    r = client.get(f"{BASE}/metrics/reports", headers=_headers("viewer"))
    assert r.status_code == 200
    data = r.json()
    assert "items" in data


# ----- Auth: read-only endpoints require auth -----


def test_product_workflows_requires_auth(client):
    """GET /api/product/v1/workflows without auth returns 401 or 403."""
    r = client.get(f"{BASE}/workflows")
    assert r.status_code in (401, 403)


def test_product_runs_requires_auth(client):
    """GET /api/product/v1/runs without auth returns 401 or 403."""
    r = client.get(f"{BASE}/runs")
    assert r.status_code in (401, 403)


# ----- RBAC: viewer cannot mutate -----


def test_product_viewer_cannot_post_run(client):
    """Viewer: POST /workflows/{id}/run returns 403."""
    r = client.post(
        f"{BASE}/workflows/some-id/run",
        json={"mode": "shadow"},
        headers=_headers("viewer"),
    )
    assert r.status_code == 403


def test_product_viewer_cannot_replay(client):
    """Viewer: POST /runs/{id}/replay returns 403."""
    r = client.post(
        f"{BASE}/runs/some-run-id/replay",
        json={"mode": "shadow"},
        headers=_headers("viewer"),
    )
    assert r.status_code == 403


def test_product_viewer_cannot_override_approval(client):
    """Viewer: POST /approvals/{id}/override returns 403."""
    r = client.post(
        f"{BASE}/approvals/some-id/override",
        json={"decision": "approve"},
        headers=_headers("viewer"),
    )
    assert r.status_code == 403


# ----- RBAC: operator can shadow run and replay -----


def test_product_operator_can_get_read_only(client):
    """Operator: GET workflows, runs, approvals returns 200."""
    for path in [f"{BASE}/workflows", f"{BASE}/runs", f"{BASE}/approvals"]:
        r = client.get(path, headers=_headers("operator"))
        assert r.status_code == 200, path


def test_product_operator_can_post_shadow_run(client):
    """Operator: POST /workflows/{id}/run with mode=shadow returns 202 or 404."""
    r = client.post(
        f"{BASE}/workflows/nonexistent/run",
        json={"mode": "shadow"},
        headers=_headers("operator"),
    )
    assert r.status_code in (202, 404, 400)


# ----- RBAC: admin can override approval -----


def test_product_admin_can_override_approval(client):
    """Admin: POST /approvals/{id}/override returns 202 or 404."""
    r = client.post(
        f"{BASE}/approvals/nonexistent-id/override",
        json={"decision": "approve"},
        headers=_headers("admin"),
    )
    assert r.status_code in (202, 404, 400)


# ----- Redaction: responses must not contain secrets -----


# Sensitive field names that must never appear in API responses (per spec)
REDACTED_KEYS = frozenset({
    "secret", "password", "api_key", "token", "raw_prompt", "internal_path",
    "prompt_dump", "credentials", "bearer",
})


def _contains_redacted(data, path=""):
    """Recursively check for redacted key names or values in dict/list."""
    if isinstance(data, dict):
        for k, v in data.items():
            key_lower = k.lower()
            if any(r in key_lower for r in REDACTED_KEYS):
                return True
            if _contains_redacted(v, f"{path}.{k}"):
                return True
    elif isinstance(data, list):
        for i, v in enumerate(data):
            if _contains_redacted(v, f"{path}[{i}]"):
                return True
    elif isinstance(data, str):
        # Value itself should not look like a secret (heuristic)
        if "sk-" in data and len(data) > 20:
            return True
    return False


def test_product_workflows_response_no_secrets(client):
    """Workflows list response must not contain secret/sensitive fields."""
    r = client.get(f"{BASE}/workflows", headers=_headers("viewer"))
    assert r.status_code == 200
    data = r.json()
    assert not _contains_redacted(data), "Response must not contain secrets"


def test_product_runs_response_no_secrets(client):
    """Runs list response must not contain secret/sensitive fields."""
    r = client.get(f"{BASE}/runs", headers=_headers("viewer"))
    assert r.status_code == 200
    data = r.json()
    assert not _contains_redacted(data), "Response must not contain secrets"


def test_product_run_detail_response_no_secrets(client):
    """Run detail (if 200) must not contain secret/sensitive fields."""
    r = client.get(f"{BASE}/runs/00000000-0000-0000-0000-000000000000", headers=_headers("viewer"))
    if r.status_code != 200:
        return
    data = r.json()
    assert not _contains_redacted(data), "Response must not contain secrets"


def test_product_approvals_response_no_secrets(client):
    """Approvals list response must not contain secrets."""
    r = client.get(f"{BASE}/approvals", headers=_headers("viewer"))
    assert r.status_code == 200
    data = r.json()
    assert not _contains_redacted(data), "Response must not contain secrets"
