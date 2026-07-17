"""U3 enterprise surfaces: audit list, system/version, brand v2, notifications."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway.store import get_store


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HG_GATEWAY_API_KEY", "test-api-key")
    monkeypatch.setenv("HG_GATEWAY_ADMIN_KEY", "test-admin-key")
    monkeypatch.setenv("HG_GATEWAY_STORE", "memory")
    if hasattr(get_store, "cache_clear"):
        get_store.cache_clear()
    store = get_store()
    if hasattr(store, "audit_append"):
        store.audit_append("default", "tenant.export", {"actor": "tester"})
    return TestClient(app)


def test_system_version(client):
    headers = {"X-API-Key": "test-api-key"}
    res = client.get("/v1/system/version", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["service"] == "hg_gateway"
    assert "build_hash" in body


def test_tenant_audit_list(client):
    headers = {"X-API-Key": "test-api-key"}
    res = client.get("/v1/tenant/audit?limit=10", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert body["total"] >= 0


def test_admin_audit_requires_admin(client):
    headers = {"X-API-Key": "test-api-key"}
    res = client.get("/v1/admin/audit", headers=headers)
    assert res.status_code in (401, 403)
    admin_headers = {"X-Admin-Key": "test-admin-key"}
    ok = client.get("/v1/admin/audit", headers=admin_headers)
    assert ok.status_code == 200
    assert "items" in ok.json()


def test_ui_brand_v2_payload(client):
    res = client.get("/v1/ui/brand", headers={"Host": "localhost"})
    assert res.status_code == 200
    body = res.json()
    assert body.get("brand_version") == 2
    assert "palettes" in body
    assert "favicon_url" in body


def test_notifications_pending_replay_payload(client):
    store = get_store()
    store.approval_add(
        "default",
        kind="tool_invoke",
        title="Pending tool approval",
        summary="test",
        risk="low",
        requested_by="test",
        payload={"type": "tool_invoke"},
    )
    from hg_gateway.routes_notifications import _pending_approval_notifications

    pending = _pending_approval_notifications(store, "default")
    assert pending
    assert pending[0]["title"] == "Pending tool approval"


def test_emit_tenant_notification_bus():
    from hg_gateway import notification_bus
    from hg_gateway.routes_notifications import emit_tenant_notification

    q = notification_bus.subscribe("default")
    try:
        emit_tenant_notification(
            "default",
            "export.completed",
            {"id": "export-default", "title": "Tenant export ready", "href": "/settings"},
        )
        event_type, payload = q.get_nowait()
        assert event_type == "export.completed"
        assert payload["title"] == "Tenant export ready"
    finally:
        notification_bus.unsubscribe("default", q)
