"""Pack 23: Gateway utility and analytics utility routes."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from hg_core.tenancy.context import TenantContext
from hg_gateway.auth import get_tenant_context, verify_api_key
from hg_gateway.main import app


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[verify_api_key] = lambda: None
    app.dependency_overrides[get_tenant_context] = lambda: TenantContext(tenant_id="default", environment="dev")
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        app.dependency_overrides.pop(get_tenant_context, None)


def test_utility_tag_means(client: TestClient) -> None:
    r = client.get("/v1/analytics/utility/tag_means")
    assert r.status_code == 200
    data = r.json()
    assert "tenant_id" in data
    assert "tag_means" in data


def test_utility_trends(client: TestClient) -> None:
    r = client.get("/v1/analytics/utility/trends", params={"window": "7d"})
    assert r.status_code == 200
    data = r.json()
    assert "tenant_id" in data
    assert "trends" in data


def test_utility_incidents(client: TestClient) -> None:
    r = client.get("/v1/analytics/utility/incidents")
    assert r.status_code == 200
    data = r.json()
    assert "tenant_id" in data
    assert "incidents" in data


def test_utility_governance_report_docx(client: TestClient) -> None:
    r = client.get("/v1/analytics/utility/governance-report", params={"format": "docx", "window": "7d"})
    assert r.status_code == 200
    data = r.json()
    if "file_id" in data:
        file_id = data["file_id"]
        r2 = client.get(f"/v1/files/{file_id}/download")
        assert r2.status_code == 200
        assert len(r2.content) > 10 * 1024, "DOCX should be > 10KB"
    else:
        assert "error" in data  # e.g. python-docx not available


def test_utility_fits(client: TestClient) -> None:
    r = client.get("/v1/utility/fits")
    assert r.status_code == 200
    data = r.json()
    assert "tenant_id" in data
    assert "fits" in data


def test_utility_drifts(client: TestClient) -> None:
    r = client.get("/v1/utility/drifts")
    assert r.status_code == 200
    data = r.json()
    assert "tenant_id" in data
    assert "drifts" in data


def test_utility_summary(client: TestClient) -> None:
    r = client.get("/v1/utility/summary")
    assert r.status_code == 200
    data = r.json()
    assert "tenant_id" in data
    assert "fits_count" in data
    assert "drifts_count" in data
