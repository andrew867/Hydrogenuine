"""Pack 15.5: Analytics API — GET /v1/analytics/signals, summary, rules/triggers, governance-report."""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from hg_core.tenancy.context import TenantContext
from hg_gateway.main import app
from hg_gateway.auth import verify_api_key, get_tenant_context


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    prev = os.environ.get("HG_GATEWAY_DB_PATH")
    os.environ["HG_GATEWAY_DB_PATH"] = path
    try:
        yield path
    finally:
        if prev is not None:
            os.environ["HG_GATEWAY_DB_PATH"] = prev
        else:
            os.environ.pop("HG_GATEWAY_DB_PATH", None)
        try:
            os.unlink(path)
        except Exception:
            pass


@pytest.fixture
def client(temp_db):
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[get_tenant_context] = lambda: TenantContext(tenant_id="default", environment="dev")
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        app.dependency_overrides.pop(get_tenant_context, None)


def test_analytics_signals_empty(client):
    r = client.get("/v1/analytics/signals")
    assert r.status_code == 200
    data = r.json()
    assert "tenant_id" in data
    assert "events" in data
    assert data["events"] == []


def test_analytics_signals_filters(client):
    r = client.get("/v1/analytics/signals", params={"chat_id": "c1", "limit": 5})
    assert r.status_code == 200
    assert r.json()["limit"] == 5


def test_analytics_summary(client):
    r = client.get("/v1/analytics/summary", params={"window": "7d"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("window") == "7d"
    assert "signal_events_count" in data
    assert "rule_triggers" in data
    assert isinstance(data["rule_triggers"], list)


def test_analytics_rules_triggers(client):
    r = client.get("/v1/analytics/rules/triggers")
    assert r.status_code == 200
    data = r.json()
    assert "triggers" in data
    assert isinstance(data["triggers"], list)


def test_analytics_governance_report_json(client):
    r = client.get("/v1/analytics/governance-report", params={"format": "json"})
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "triggers" in data
