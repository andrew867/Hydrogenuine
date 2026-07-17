"""
Tenant-admin and principal auth: role and principal_id in GET /tenants/me,
principals disabled, principal-scoped approvals filter.
Uses real auth (no override); set env for keys.
"""

import os
import pytest
from fastapi.testclient import TestClient

from hg_gateway.main import app
from hg_gateway import store as store_module
from hg_gateway.auth import (
    TENANT_ADMIN_KEYS_ENV,
    PRINCIPAL_KEYS_ENV,
    TENANT_BY_KEY_ENV,
    ENV_KEY,
    DEV_ENV,
    ADMIN_KEY_ENV,
)


@pytest.fixture
def client_sqlite(tmp_path):
    """Client with SQLite store; real auth from env."""
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_DB_PATH"] = str(tmp_path / "gateway.sqlite3")
    os.environ[DEV_ENV] = "1"
    os.environ[ENV_KEY] = "op1"
    os.environ[TENANT_BY_KEY_ENV] = "op1:default"
    os.environ[TENANT_ADMIN_KEYS_ENV] = "op1"
    os.environ[ADMIN_KEY_ENV] = "admin-secret"
    store_module._store = None
    try:
        yield TestClient(app)
    finally:
        store_module._store = None
        for k in ("HG_GATEWAY_STORE", "HG_GATEWAY_DB_PATH", DEV_ENV, ENV_KEY, TENANT_BY_KEY_ENV, TENANT_ADMIN_KEYS_ENV, PRINCIPAL_KEYS_ENV, ADMIN_KEY_ENV):
            os.environ.pop(k, None)


def test_tenants_me_returns_role_operator(client_sqlite):
    """Operator key (not in tenant_admin) gets role operator."""
    os.environ[TENANT_ADMIN_KEYS_ENV] = ""  # op1 is not tenant_admin
    r = client_sqlite.get("/v1/tenants/me", headers={"Authorization": "Bearer op1"})
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == "default"
    assert data.get("role") == "operator"
    assert "principal_id" not in data


def test_tenants_me_returns_role_tenant_admin(client_sqlite):
    """Key in TENANT_ADMIN_KEYS gets role tenant_admin."""
    r = client_sqlite.get("/v1/tenants/me", headers={"Authorization": "Bearer op1"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("role") == "tenant_admin"
    assert data["tenant_id"] == "default"


def test_tenants_me_returns_role_principal_and_principal_id(client_sqlite):
    """Principal key gets role principal and principal_id."""
    # GET /tenants/me for principal requires the principal to exist in DB
    client_sqlite.post(
        "/v1/principals",
        json={"id": "principal_1", "type": "user", "label": "P1", "status": "online"},
        headers={"Authorization": "Bearer op1"},
    )
    os.environ[PRINCIPAL_KEYS_ENV] = "key_p1:default:principal_1"
    r = client_sqlite.get("/v1/tenants/me", headers={"Authorization": "Bearer key_p1"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("role") == "principal"
    assert data.get("principal_id") == "principal_1"
    assert data["tenant_id"] == "default"


def test_tenants_me_allows_browser_principal_without_local_row(client_sqlite):
    """Browser-backed principal sessions should still get tenant identity even before local provisioning exists."""
    os.environ[PRINCIPAL_KEYS_ENV] = "key_p_missing:default:principal_missing"
    r = client_sqlite.get("/v1/tenants/me", headers={"Authorization": "Bearer key_p_missing"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("role") == "principal"
    assert data.get("principal_id") == "principal_missing"
    assert data.get("principal_missing") is True


def test_tenants_me_403_when_principal_disabled(client_sqlite):
    """When principal key maps to a disabled principal, GET /tenants/me returns 403."""
    os.environ[PRINCIPAL_KEYS_ENV] = "key_p2:default:principal_2"
    # Create principal_2 as operator, then disable via DB
    r = client_sqlite.post(
        "/v1/principals",
        json={"id": "principal_2", "type": "user", "label": "P2", "status": "offline"},
        headers={"Authorization": "Bearer op1"},
    )
    assert r.status_code == 200
    r = client_sqlite.patch(
        "/v1/principals/principal_2/availability",
        json={"disabled": True},
        headers={"Authorization": "Bearer op1"},
    )
    assert r.status_code == 200
    r = client_sqlite.get("/v1/tenants/me", headers={"Authorization": "Bearer key_p2"})
    assert r.status_code == 403


def test_tenant_me_settings_readable_by_principal(client_sqlite):
    """Principal sessions can read tenant settings in read-only mode."""
    os.environ[PRINCIPAL_KEYS_ENV] = "key_p_settings:default:principal_settings"
    r = client_sqlite.get("/v1/tenants/me/settings", headers={"Authorization": "Bearer key_p_settings"})
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == "default"
    assert data.get("can_edit") is False


def test_tenant_admin_can_store_targeted_approval_rules(client_sqlite):
    """Tenant settings accept targeted approval rules for workflow/kind/risk controls."""
    r = client_sqlite.patch(
        "/v1/tenants/me/settings",
        json={
            "approval_rules": [
                {
                    "id": "social-posts",
                    "label": "Auto approve fourclaw posts",
                    "enabled": True,
                    "decision": "auto_approve",
                    "kinds": ["social_write"],
                    "risks": ["high"],
                    "workflow_ids": ["fourclaw-auto-post"],
                    "platforms": ["fourclaw"],
                    "modes": ["post"],
                }
            ]
        },
        headers={"Authorization": "Bearer op1"},
    )
    assert r.status_code == 200
    r = client_sqlite.get("/v1/tenants/me/settings", headers={"Authorization": "Bearer op1"})
    assert r.status_code == 200
    data = r.json()
    assert len(data.get("approval_rules") or []) == 1
    rule = data["approval_rules"][0]
    assert rule["workflow_ids"] == ["fourclaw-auto-post"]
    assert rule["kinds"] == ["social_write"]


def test_principals_list_excludes_disabled_by_default(client_sqlite):
    """list_principals excludes disabled unless include_disabled=true."""
    client_sqlite.post(
        "/v1/principals",
        json={"id": "a", "type": "user", "label": "A", "status": "online"},
        headers={"Authorization": "Bearer op1"},
    )
    client_sqlite.post(
        "/v1/principals",
        json={"id": "b", "type": "user", "label": "B", "status": "offline"},
        headers={"Authorization": "Bearer op1"},
    )
    client_sqlite.patch(
        "/v1/principals/b/availability",
        json={"disabled": True},
        headers={"Authorization": "Bearer op1"},
    )
    r = client_sqlite.get("/v1/principals", headers={"Authorization": "Bearer op1"})
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()["principals"]]
    assert "a" in ids
    assert "b" not in ids
    r2 = client_sqlite.get("/v1/principals?include_disabled=true", headers={"Authorization": "Bearer op1"})
    assert r2.status_code == 200
    ids2 = [p["id"] for p in r2.json()["principals"]]
    assert "a" in ids2
    assert "b" in ids2
    assert next(p for p in r2.json()["principals"] if p["id"] == "b")["disabled"] is True


def test_principals_list_403_when_operator(client_sqlite):
    """Pack 13: Operator (not tenant_admin) cannot list principals."""
    os.environ[TENANT_ADMIN_KEYS_ENV] = ""  # op1 is operator only
    r = client_sqlite.get("/v1/principals", headers={"Authorization": "Bearer op1"})
    assert r.status_code == 403


def test_principals_list_403_when_principal(client_sqlite):
    """Principal-scoped caller cannot list principals."""
    os.environ[PRINCIPAL_KEYS_ENV] = "key_p3:default:principal_3"
    client_sqlite.post(
        "/v1/principals",
        json={"id": "principal_3", "type": "user", "label": "P3", "status": "online"},
        headers={"Authorization": "Bearer op1"},
    )
    r = client_sqlite.get("/v1/principals", headers={"Authorization": "Bearer key_p3"})
    assert r.status_code == 403


def test_approvals_filtered_by_assigned_principal(client_sqlite):
    """When principal key is used, GET /approvals returns only approvals assigned to that principal."""
    os.environ[PRINCIPAL_KEYS_ENV] = "key_p4:default:principal_4"
    # Create two principals; principal_4 is in chain so gets assigned
    client_sqlite.post(
        "/v1/principals",
        json={"id": "principal_4", "type": "user", "label": "P4", "status": "online", "escalation_chain": ["principal_4"]},
        headers={"Authorization": "Bearer op1"},
    )
    client_sqlite.post(
        "/v1/principals",
        json={"id": "other", "type": "user", "label": "Other", "status": "offline"},
        headers={"Authorization": "Bearer op1"},
    )
    r = client_sqlite.post("/v1/chats", json={"title": "Chat"}, headers={"Authorization": "Bearer op1"})
    chat_id = r.json()["chat_id"]
    client_sqlite.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Hi"},
        headers={"Authorization": "Bearer op1"},
    )
    r = client_sqlite.get("/v1/approvals", headers={"Authorization": "Bearer op1"})
    assert r.status_code == 200
    approvals_op = r.json()["approvals"]
    assert len(approvals_op) == 1
    r = client_sqlite.get("/v1/approvals", headers={"Authorization": "Bearer key_p4"})
    assert r.status_code == 200
    approvals_principal = r.json()["approvals"]
    assert len(approvals_principal) == 1
    assert approvals_principal[0].get("assignedPrincipalId") == "principal_4"


def test_principal_can_only_get_self(client_sqlite):
    """Principal can GET /principals/{self} but not another principal."""
    os.environ[PRINCIPAL_KEYS_ENV] = "key_p5:default:principal_5"
    client_sqlite.post(
        "/v1/principals",
        json={"id": "principal_5", "type": "user", "label": "P5", "status": "online"},
        headers={"Authorization": "Bearer op1"},
    )
    client_sqlite.post(
        "/v1/principals",
        json={"id": "other2", "type": "user", "label": "Other2", "status": "offline"},
        headers={"Authorization": "Bearer op1"},
    )
    r = client_sqlite.get("/v1/principals/principal_5", headers={"Authorization": "Bearer key_p5"})
    assert r.status_code == 200
    assert r.json()["id"] == "principal_5"
    r2 = client_sqlite.get("/v1/principals/other2", headers={"Authorization": "Bearer key_p5"})
    assert r2.status_code == 403


def test_impersonate_returns_token_and_tenants_me_impersonating(client_sqlite):
    """Pack 13: POST /v1/admin/impersonate returns token; using it in GET /tenants/me returns impersonating true."""
    r = client_sqlite.post(
        "/v1/admin/impersonate",
        json={"tenant_id": "default", "role": "operator"},
        headers={"Authorization": "Bearer op1", "X-API-Key": "op1", "X-Admin-Key": "admin-secret"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "token" in data
    assert "expires_at" in data
    token = data["token"]
    r2 = client_sqlite.get("/v1/tenants/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    me = r2.json()
    assert me.get("impersonating") is True
    assert me.get("impersonation_tenant_id") == "default"
    assert me["tenant_id"] == "default"
