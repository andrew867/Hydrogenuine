"""
Pack 13: Admin tenant CRUD, domains, keys, usage, export, delete, impersonate.
Integration tests with SQLite store and real auth.
"""

import os
import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import ENV_KEY, DEV_ENV, TENANT_BY_KEY_ENV, ADMIN_KEY_ENV


@pytest.fixture
def client_sqlite(tmp_path):
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    os.environ[DEV_ENV] = "1"
    os.environ[ENV_KEY] = "op1"
    os.environ[TENANT_BY_KEY_ENV] = "op1:default"
    os.environ[ADMIN_KEY_ENV] = "admin-secret"
    store_module._store = None
    try:
        yield TestClient(app)
    finally:
        store_module._store = None
        for k in ("HG_GATEWAY_STORE", "HG_GATEWAY_DB_PATH", DEV_ENV, ENV_KEY, TENANT_BY_KEY_ENV, ADMIN_KEY_ENV):
            os.environ.pop(k, None)


def _admin_headers():
    return {"Authorization": "Bearer op1", "X-API-Key": "op1", "X-Admin-Key": "admin-secret"}


def test_admin_list_tenants(client_sqlite):
    """GET /v1/admin/tenants returns tenants list with pagination."""
    r = client_sqlite.get("/v1/admin/tenants", headers=_admin_headers())
    assert r.status_code == 200
    data = r.json()
    assert "tenants" in data
    assert "total" in data
    assert isinstance(data["tenants"], list)


def test_admin_create_and_get_tenant(client_sqlite):
    """POST /v1/admin/tenants creates; GET /v1/admin/tenants/{id} returns it."""
    r = client_sqlite.post(
        "/v1/admin/tenants",
        json={"tenant_id": "acme", "display_name": "Acme Corp"},
        headers=_admin_headers(),
    )
    assert r.status_code == 200
    assert r.json().get("tenant_id") == "acme"
    r2 = client_sqlite.get("/v1/admin/tenants/acme", headers=_admin_headers())
    assert r2.status_code == 200
    data = r2.json()
    assert data["tenant_id"] == "acme"
    assert data.get("display_name") == "Acme Corp"
    assert "domains" in data
    assert "usage" in data


def test_admin_create_tenant_key_returns_key_once(client_sqlite):
    """POST /v1/admin/tenants/{id}/keys returns raw key; key authenticates as that tenant."""
    client_sqlite.post(
        "/v1/admin/tenants",
        json={"tenant_id": "keytenant", "display_name": "Key Tenant"},
        headers=_admin_headers(),
    )
    r = client_sqlite.post("/v1/admin/tenants/keytenant/keys", headers=_admin_headers())
    assert r.status_code == 200
    data = r.json()
    assert "key" in data
    assert data.get("tenant_id") == "keytenant"
    raw_key = data["key"]
    assert raw_key.startswith("hg_")
    r2 = client_sqlite.get("/v1/tenants/me", headers={"Authorization": f"Bearer {raw_key}"})
    assert r2.status_code == 200
    assert r2.json()["tenant_id"] == "keytenant"


def test_admin_export_tenant(client_sqlite):
    """POST /v1/admin/tenants/{id}/export returns export JSON."""
    r = client_sqlite.post("/v1/admin/tenants/default/export", headers=_admin_headers())
    assert r.status_code == 200
    data = r.json()
    assert "tenant_id" in data or "chats" in data


def test_admin_delete_tenant_requires_confirm(client_sqlite):
    """POST /v1/admin/tenants/{id}/delete without confirm_tenant_id returns 400."""
    client_sqlite.post(
        "/v1/admin/tenants",
        json={"tenant_id": "todel", "display_name": "To Delete"},
        headers=_admin_headers(),
    )
    r = client_sqlite.post(
        "/v1/admin/tenants/todel/delete",
        json={},
        headers=_admin_headers(),
    )
    assert r.status_code == 400
    r2 = client_sqlite.post(
        "/v1/admin/tenants/todel/delete",
        json={"confirm_tenant_id": "todel"},
        headers=_admin_headers(),
    )
    assert r2.status_code == 200


def test_admin_list_tenants_accepts_admin_bearer_without_operator_key(client_sqlite):
    r = client_sqlite.get("/v1/admin/tenants", headers={"Authorization": "Bearer admin-secret"})
    assert r.status_code == 200
    data = r.json()
    assert "tenants" in data
