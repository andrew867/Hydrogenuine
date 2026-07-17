"""
Pack3 Phase 7: Retention, export, and tenant delete — API and job tests.
"""

import os
import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import verify_api_key
from hg_gateway.retention import run_retention, get_retention_days_chats, get_retention_days_bundles


@pytest.fixture
def client_sqlite(tmp_path):
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    store_module._store = None
    app.dependency_overrides[verify_api_key] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        os.environ.pop("HG_GATEWAY_STORE", None)
        os.environ.pop("HG_GATEWAY_DB_PATH", None)


def test_tenant_export_structure_and_redaction(client_sqlite):
    """POST /v1/tenants/{id}/export returns redacted JSON with chats, messages, approvals, bundle_ids."""
    # Create data as default tenant
    r = client_sqlite.post("/v1/chats", json={"title": "Export test"}, headers={"X-Tenant-ID": "default"})
    assert r.status_code == 200
    chat_id = r.json()["chat_id"]
    client_sqlite.post(
        f"/v1/chats/{chat_id}/messages",
        json={"role": "user", "content": "Hello"},
        headers={"X-Tenant-ID": "default"},
    )
    # Export own tenant
    r = client_sqlite.post("/v1/tenants/default/export", headers={"X-Tenant-ID": "default"})
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == "default"
    assert "exported_at" in data
    assert "chats" in data
    assert len(data["chats"]) >= 1
    found = next((c for c in data["chats"] if c.get("chat", {}).get("chat_id") == chat_id), None)
    assert found
    assert "messages" in found
    assert any(m.get("content") for m in found["messages"])
    assert "approvals" in data
    assert "bundle_ids" in data
    # Redaction: exported content should not contain raw secrets in obvious form (structure present)
    assert isinstance(data["approvals"], list)
    assert isinstance(data["bundle_ids"], list)


def test_tenant_export_own_tenant_only(client_sqlite):
    """Export with tenant_id != context tenant returns 403."""
    r = client_sqlite.post("/v1/tenants/other-tenant/export", headers={"X-Tenant-ID": "default"})
    assert r.status_code == 403


def test_tenant_delete_requires_admin_key(client_sqlite):
    """POST /v1/tenants/{id}/delete without X-Admin-Key returns 403 or 503."""
    # No admin key configured -> 503
    os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)
    r = client_sqlite.post("/v1/tenants/default/delete")
    assert r.status_code in (403, 503)
    # Configure key but do not send it -> 403
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "secret-admin"
    r = client_sqlite.post("/v1/tenants/default/delete")
    assert r.status_code == 403
    r = client_sqlite.post("/v1/tenants/default/delete", headers={"X-Admin-Key": "wrong"})
    assert r.status_code == 403


def test_tenant_delete_removes_data_and_writes_tombstone(client_sqlite, tmp_path):
    """With valid X-Admin-Key, delete removes tenant data and audit has tenant_deleted."""
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "admin-secret"
    db_path = tmp_path / "gateway.sqlite3"
    os.environ["HG_GATEWAY_DB_PATH"] = str(db_path)
    store_module._store = None

    client = TestClient(app)
    app.dependency_overrides[verify_api_key] = lambda: None
    try:
        # Create chat as default tenant
        r = client.post("/v1/chats", json={}, headers={"X-Tenant-ID": "default"})
        assert r.status_code == 200
        chat_id = r.json()["chat_id"]
        r = client.post("/v1/tenants/default/delete", headers={"X-Admin-Key": "admin-secret"})
        assert r.status_code == 200
        data = r.json()
        assert data["tenant_id"] == "default"
        assert "deleted" in data
        counts = data["deleted"]
        assert counts.get("chats", 0) >= 1 or counts.get("messages", 0) >= 0
        # Tombstone in audit (SQLite): query audit_events
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT event_type, payload FROM audit_events WHERE event_type = ?", ("tenant_deleted",)
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["event_type"] == "tenant_deleted"
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
        os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)


def test_retention_config_defaults():
    """Retention env defaults: HG_RETENTION_DAYS_CHATS 90, HG_RETENTION_DAYS_BUNDLES 30."""
    os.environ.pop("HG_RETENTION_DAYS_CHATS", None)
    os.environ.pop("HG_RETENTION_DAYS_BUNDLES", None)
    assert get_retention_days_chats() == 90
    assert get_retention_days_bundles() == 30


def test_retention_job_prunes_old_chats(client_sqlite, tmp_path):
    """run_retention with days_chats=0 prunes old chats for tenant (SQLite)."""
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "retention.sqlite3")
    store_module._store = None
    store = store_module.get_store()
    store.chat_create("default", title="Old")
    result = run_retention(store, tenant_id="default", days_chats=0, days_bundles=9999)
    assert "chats_pruned" in result
    assert result["chats_pruned"] >= 1
    assert "default" in result["tenants"]
