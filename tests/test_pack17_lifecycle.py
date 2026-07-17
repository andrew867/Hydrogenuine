"""Pack 17: Data lifecycle — retention policy, export archive with manifest, legal hold, purge."""

import os
import zipfile
import io
import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway.db import get_connection


@pytest.fixture
def gateway_with_sqlite(tmp_path):
    """Gateway with SQLite and v21 migration (tenant_retention)."""
    db_path = str(tmp_path / "gateway.db")
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_DB_PATH"] = db_path
    with get_connection(db_path) as conn:
        pass  # trigger migration
    client = TestClient(app)
    yield client
    os.environ.pop("HG_GATEWAY_STORE", None)
    os.environ.pop("HG_GATEWAY_DB_PATH", None)


def test_retention_policy_get_default(gateway_with_sqlite):
    """GET /v1/tenant/retention returns default policy for tenant."""
    client = gateway_with_sqlite
    os.environ["HG_GATEWAY_API_KEY"] = "lifecycle-key"
    os.environ["HG_GATEWAY_TENANT_BY_KEY"] = "lifecycle-key:tenant1"
    try:
        r = client.get("/v1/tenant/retention", headers={"X-API-Key": "lifecycle-key"})
        assert r.status_code == 200
        data = r.json()
        assert data["tenant_id"] == "tenant1"
        assert data["chats_days"] == 90
        assert data["proofs_days"] == 30
        assert "legal_hold_enabled" in data
    finally:
        os.environ.pop("HG_GATEWAY_API_KEY", None)
        os.environ.pop("HG_GATEWAY_TENANT_BY_KEY", None)


def test_retention_policy_patch(gateway_with_sqlite):
    """PATCH /v1/tenant/retention updates policy; requires tenant_admin."""
    client = gateway_with_sqlite
    os.environ["HG_GATEWAY_API_KEY"] = "admin-lifecycle"
    os.environ["HG_GATEWAY_TENANT_BY_KEY"] = "admin-lifecycle:tenant1"
    os.environ["HG_GATEWAY_TENANT_ADMIN_KEYS"] = "admin-lifecycle"
    try:
        r = client.patch(
            "/v1/tenant/retention",
            headers={"X-API-Key": "admin-lifecycle", "Content-Type": "application/json"},
            json={"chats_days": 60, "legal_hold_enabled": True},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["chats_days"] == 60
        assert data["legal_hold_enabled"] is True
        r2 = client.get("/v1/tenant/retention", headers={"X-API-Key": "admin-lifecycle"})
        assert r2.json()["legal_hold_enabled"] is True
    finally:
        os.environ.pop("HG_GATEWAY_API_KEY", None)
        os.environ.pop("HG_GATEWAY_TENANT_BY_KEY", None)
        os.environ.pop("HG_GATEWAY_TENANT_ADMIN_KEYS", None)


def test_tenant_export_archive(gateway_with_sqlite):
    """POST /v1/tenant/export returns zip with export.json and manifest (sha256)."""
    client = gateway_with_sqlite
    os.environ["HG_GATEWAY_API_KEY"] = "export-key"
    os.environ["HG_GATEWAY_TENANT_BY_KEY"] = "export-key:tenant1"
    try:
        r = client.post("/v1/tenant/export", headers={"X-API-Key": "export-key"})
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/zip")
        z = zipfile.ZipFile(io.BytesIO(r.content), "r")
        names = z.namelist()
        assert "export.json" in names
        assert "manifest.json" in names
        manifest = z.read("manifest.json")
        import json
        m = json.loads(manifest)
        assert "export.json" in m
        assert len(m["export.json"]) == 64  # sha256 hex
    finally:
        os.environ.pop("HG_GATEWAY_API_KEY", None)
        os.environ.pop("HG_GATEWAY_TENANT_BY_KEY", None)


def test_admin_purge_blocks_legal_hold(gateway_with_sqlite):
    """Admin purge returns 403 when tenant has legal_hold_enabled."""
    client = gateway_with_sqlite
    os.environ["HG_GATEWAY_API_KEY"] = "admin-key"
    os.environ["HG_GATEWAY_TENANT_BY_KEY"] = "admin-key:default"
    os.environ["HG_GATEWAY_TENANT_ADMIN_KEYS"] = "admin-key"
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "admin-key"
    try:
        # Enable legal hold for default
        client.patch(
            "/v1/tenant/retention",
            headers={"X-API-Key": "admin-key", "Content-Type": "application/json"},
            json={"legal_hold_enabled": True},
        )
        r = client.post(
            "/v1/admin/tenants/default/purge",
            headers={"X-API-Key": "admin-key", "X-Admin-Key": "admin-key", "Content-Type": "application/json"},
            json={},
        )
        assert r.status_code == 403
        assert "legal hold" in (r.json().get("detail") or "").lower()
    finally:
        for k in ["HG_GATEWAY_API_KEY", "HG_GATEWAY_TENANT_BY_KEY", "HG_GATEWAY_TENANT_ADMIN_KEYS", "HG_GATEWAY_ADMIN_KEY"]:
            os.environ.pop(k, None)
