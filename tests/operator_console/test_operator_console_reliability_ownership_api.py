"""API tests for Operator Console reliability and ownership endpoints."""

import sys
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[2]
_server_path = _workspace / "operator_console" / "server"
if _server_path.exists():
    sys.path.insert(0, str(_workspace))
    sys.path.insert(0, str(_server_path))
    from fastapi.testclient import TestClient
    from app.main import app
    _client_fixture = lambda: TestClient(app)
else:
    app = None
    _client_fixture = None


def _headers():
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def client():
    if _client_fixture is None:
        pytest.skip("operator_console/server not found")
    return _client_fixture()


def test_reliability_failure_classes(client):
    """GET /api/v1/reliability/failure-classes returns list of failure classes."""
    r = client.get("/api/v1/reliability/failure-classes", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "classes" in data
    assert isinstance(data["classes"], list)
    assert "transient_network" in data["classes"]
    assert "unknown" in data["classes"]


def test_reliability_retry_policy_all(client):
    """GET /api/v1/reliability/retry-policy returns policies for all classes."""
    r = client.get("/api/v1/reliability/retry-policy", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "policies" in data
    assert "transient_network" in data["policies"]
    p = data["policies"]["transient_network"]
    assert "max_attempts" in p
    assert "retryable" in p


def test_reliability_retry_policy_one(client):
    """GET /api/v1/reliability/retry-policy?class=transient_network returns single policy."""
    r = client.get(
        "/api/v1/reliability/retry-policy",
        params={"class_name": "transient_network"},
        headers=_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "policy" in data
    assert data.get("class") == "transient_network"
    assert data["policy"].get("retryable") is True


def test_reliability_breakers(client):
    """GET /api/v1/reliability/breakers returns list of breakers."""
    r = client.get("/api/v1/reliability/breakers", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "breakers" in data
    assert isinstance(data["breakers"], list)


def test_reliability_breakers_reset(client):
    """POST /api/v1/reliability/breakers/reset returns ok."""
    r = client.post(
        "/api/v1/reliability/breakers/reset",
        headers=_headers(),
        json={"workflow_id": "test-workflow", "destination": None},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True


def test_reliability_incident_queue(client):
    """GET /api/v1/reliability/incident-queue returns items list."""
    r = client.get("/api/v1/reliability/incident-queue", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "items" in data
    assert isinstance(data["items"], list)


def test_reliability_budget_summary(client):
    """GET /api/v1/reliability/budget-summary returns by_workflow and recent_runs."""
    r = client.get("/api/v1/reliability/budget-summary", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "by_workflow" in data
    assert "recent_runs" in data
    assert isinstance(data["by_workflow"], dict)
    assert isinstance(data["recent_runs"], int)


def test_ownership_conflicts(client):
    """GET /api/v1/ownership/conflicts returns conflicts list."""
    r = client.get("/api/v1/ownership/conflicts", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "conflicts" in data
    assert isinstance(data["conflicts"], list)


def test_ownership_handoffs(client):
    """GET /api/v1/ownership/handoffs returns events list."""
    r = client.get("/api/v1/ownership/handoffs", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert "events" in data
    assert isinstance(data["events"], list)
