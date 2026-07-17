"""Product API parity endpoints for templates and audit export."""

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


def _existing_workflow_id(client):
    resp = client.get(f"{BASE}/workflows", headers=_headers("viewer"))
    if resp.status_code != 200:
        return None
    items = resp.json().get("items", [])
    if not items:
        return None
    return items[0].get("id")


def test_product_templates_list(client):
    r = client.get(f"{BASE}/templates", headers=_headers("viewer"))
    assert r.status_code == 200
    data = r.json()
    assert "items" in data


def test_product_template_instantiate_contract(client):
    list_resp = client.get(f"{BASE}/templates", headers=_headers("viewer"))
    assert list_resp.status_code == 200
    items = list_resp.json().get("items", [])
    if not items:
        pytest.skip("no templates available in this test environment")

    template_id = items[0]["template_id"]
    payload = {"goal": "parity smoke", "context": {"source": "pytest"}}
    r = client.post(
        f"{BASE}/templates/{template_id}/instantiate",
        json=payload,
        headers=_headers("operator"),
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("template_id") == template_id
    assert isinstance(data.get("dag"), dict)
    assert isinstance(data.get("dag", {}).get("nodes", []), list)


def test_product_operator_run_accepts_template_id(client):
    list_resp = client.get(f"{BASE}/templates", headers=_headers("viewer"))
    assert list_resp.status_code == 200
    items = list_resp.json().get("items", [])
    template_id = items[0]["template_id"] if items else None

    body = {"mode": "shadow"}
    if template_id:
        body["template_id"] = template_id
    wf_id = _existing_workflow_id(client)
    if not wf_id:
        pytest.skip("no workflows available in this environment")
    r = client.post(f"{BASE}/workflows/{wf_id}/run", json=body, headers=_headers("operator"))
    assert r.status_code == 202
    data = r.json()
    assert data.get("accepted") is True
    assert data.get("mode") == "shadow"
    if template_id:
        assert data.get("template_id") == template_id


def test_product_viewer_cannot_rollback(client):
    r = client.post(f"{BASE}/runs/some-run-id/rollback", json={"mode": "shadow"}, headers=_headers("viewer"))
    assert r.status_code == 403


def test_product_operator_rollback_contract(client):
    r = client.post(f"{BASE}/runs/some-run-id/rollback", json={"mode": "shadow"}, headers=_headers("operator"))
    assert r.status_code in (202, 404)


def test_product_audit_report_not_found(client):
    r = client.get(f"{BASE}/runs/not-a-run/audit-report", headers=_headers("viewer"))
    assert r.status_code == 404
