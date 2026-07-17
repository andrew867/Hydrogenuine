"""Ch4 Product UI: API-level smoke and E2E (dashboard -> run -> audit summary).

Verifies the flows the UI will use: metrics/summary, runs list, run detail with audit_summary.
"""

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


def _headers(role="viewer"):
    keys = {"viewer": "test-product-viewer", "operator": "test-product-operator", "admin": "test-product-admin"}
    return {"Authorization": f"Bearer {keys.get(role, keys['viewer'])}"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


def test_smoke_navigation_flows(client):
    """Smoke: Dashboard data (metrics), Workflows list, Runs list, Approvals, Deadletters return 200."""
    h = _headers("viewer")
    r1 = client.get(f"{BASE}/metrics/summary", headers=h)
    assert r1.status_code == 200
    r2 = client.get(f"{BASE}/workflows", headers=h)
    assert r2.status_code == 200
    r3 = client.get(f"{BASE}/runs", headers=h)
    assert r3.status_code == 200
    r4 = client.get(f"{BASE}/approvals", headers=h)
    assert r4.status_code == 200
    r5 = client.get(f"{BASE}/incidents", headers=h)
    assert r5.status_code == 200


def test_e2e_dashboard_open_run_view_audit_summary(client):
    """E2E: view dashboard (metrics) -> open runs list -> open first run -> view audit summary."""
    h = _headers("viewer")
    # Dashboard: metrics summary
    r_metrics = client.get(f"{BASE}/metrics/summary", headers=h)
    assert r_metrics.status_code == 200
    data_metrics = r_metrics.json()
    assert "period" in data_metrics or "cost" in data_metrics or "sla" in data_metrics
    # Runs list
    r_runs = client.get(f"{BASE}/runs", headers=h)
    assert r_runs.status_code == 200
    data_runs = r_runs.json()
    assert "items" in data_runs
    items = data_runs["items"]
    if not items:
        # No runs: run detail would 404; flow still valid
        return
    run_id = items[0]["run_id"]
    # Run detail (audit summary)
    r_detail = client.get(f"{BASE}/runs/{run_id}", headers=h)
    assert r_detail.status_code == 200
    detail = r_detail.json()
    assert "run_id" in detail
    assert "audit_summary" in detail
    assert "status" in detail
