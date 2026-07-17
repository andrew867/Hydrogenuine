"""
Pack 16: Tests for auth (session store, /auth/me, /auth/sessions) and SCIM (/scim/v2/Users, /scim/v2/Groups).
RBAC: deny-by-default; viewer cannot access tenant_admin-only actions.
"""

import os
import pytest
from fastapi.testclient import TestClient

# Use in-memory DB for tests
os.environ["HG_GATEWAY_STORE"] = "memory"
os.environ["HG_GATEWAY_DEV"] = "1"


@pytest.fixture
def client():
    from hg_gateway.main import app
    return TestClient(app)


@pytest.fixture
def gateway_with_sqlite(tmp_path):
    """Use temp SQLite so sessions and SCIM tables exist."""
    db_path = str(tmp_path / "gateway.sqlite3")
    os.environ["HG_GATEWAY_STORE"] = "sqlite"
    os.environ["HG_GATEWAY_DB_PATH"] = db_path
    from hg_gateway.main import app
    yield TestClient(app)
    os.environ.pop("HG_GATEWAY_DB_PATH", None)
    os.environ["HG_GATEWAY_STORE"] = "memory"


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_auth_me_unauthenticated(client):
    """Without session cookie, /auth/me returns 401."""
    r = client.get("/v1/auth/me")
    assert r.status_code == 401


def test_auth_me_with_invalid_session(client):
    """Invalid session cookie returns 401."""
    r = client.get("/v1/auth/me", cookies={"hg_session": "invalid-sid"})
    assert r.status_code == 401


def test_auth_sessions_unauthenticated(client):
    r = client.get("/v1/auth/sessions")
    assert r.status_code == 401


def test_oidc_start_disabled(client):
    """When OIDC not enabled, /auth/oidc/start returns 501."""
    r = client.get("/v1/auth/oidc/start", params={"frontend_redirect_uri": "http://localhost:3000/"})
    assert r.status_code == 501


def test_oidc_start_sets_state_cookies_and_forces_login(gateway_with_sqlite):
    client = gateway_with_sqlite
    os.environ["HG_OIDC_ENABLED"] = "1"
    os.environ["KEYCLOAK_PUBLIC_URL"] = "http://localhost:8180"
    os.environ["KEYCLOAK_REALM"] = "hg"
    os.environ["KEYCLOAK_CLIENT_ID"] = "gateway-ui"
    try:
        r = client.get("/v1/auth/oidc/start", params={"frontend_redirect_uri": "http://localhost:3000/"}, follow_redirects=False)
        assert r.status_code == 302
        location = r.headers["location"]
        assert "prompt=login" in location
        assert "code_challenge_method=S256" in location
        assert r.cookies.get("hg_oidc_state")
        assert r.cookies.get("hg_oidc_redirects")
    finally:
        os.environ.pop("HG_OIDC_ENABLED", None)
        os.environ.pop("KEYCLOAK_PUBLIC_URL", None)
        os.environ.pop("KEYCLOAK_REALM", None)
        os.environ.pop("KEYCLOAK_CLIENT_ID", None)


def test_resolve_oidc_roles_supports_resource_access_and_demo_fallback():
    from hg_gateway.auth_routes import _resolve_oidc_roles

    payload = {
        "preferred_username": "demo-superadmin",
        "resource_access": {"gateway-ui": {"roles": ["operator"]}},
        "groups": ["/tenant-admin"],
    }

    roles = _resolve_oidc_roles(payload, "gateway-ui")

    assert "superadmin" in roles
    assert "operator" in roles
    assert "tenant_admin" in roles


def test_oidc_logout_includes_id_token_hint_when_present(gateway_with_sqlite):
    client = gateway_with_sqlite
    os.environ["HG_OIDC_ENABLED"] = "1"
    os.environ["KEYCLOAK_PUBLIC_URL"] = "http://localhost:8180"
    os.environ["KEYCLOAK_REALM"] = "hg"
    os.environ["KEYCLOAK_CLIENT_ID"] = "gateway-ui"
    try:
      response = client.get(
          "/v1/auth/oidc/logout",
          params={"frontend_redirect_uri": "http://localhost:3000/"},
          cookies={"hg_oidc_id_token": "id-token-demo"},
          follow_redirects=False,
      )
      assert response.status_code == 302
      location = response.headers["location"]
      assert "id_token_hint=id-token-demo" in location
      assert "post_logout_redirect_uri=http%3A%2F%2Flocalhost%3A3000%2F" in location
    finally:
        os.environ.pop("HG_OIDC_ENABLED", None)
        os.environ.pop("KEYCLOAK_PUBLIC_URL", None)
        os.environ.pop("KEYCLOAK_REALM", None)
        os.environ.pop("KEYCLOAK_CLIENT_ID", None)


def test_auth_config_exposes_browser_auth_shape(client):
    r = client.get("/v1/auth/config")
    assert r.status_code == 200
    body = r.json()
    assert body["supports_key_exchange_login"] is True
    assert body["session_cookie_name"] == "hg_session"


def test_auth_session_login_with_operator_key_and_cookie_auth(gateway_with_sqlite):
    client = gateway_with_sqlite
    os.environ["HG_GATEWAY_API_KEY"] = "op-test-key"
    os.environ["HG_GATEWAY_TENANT_BY_KEY"] = "op-test-key:tenant-r2"
    try:
        login = client.post("/v1/auth/session/login", json={"operator_key": "op-test-key"})
        assert login.status_code == 200
        payload = login.json()
        assert payload["tenant_id"] == "tenant-r2"
        assert payload["principal_id"] == "operator"
        assert "operator" in payload["roles"]
        assert login.cookies.get("hg_session")

        me = client.get("/v1/auth/me", cookies=login.cookies)
        assert me.status_code == 200
        assert me.json()["tenant_id"] == "tenant-r2"

        summary = client.get("/v1/utility/summary", cookies=login.cookies)
        assert summary.status_code == 200
        assert summary.json()["tenant_id"] == "tenant-r2"
    finally:
        os.environ.pop("HG_GATEWAY_API_KEY", None)
        os.environ.pop("HG_GATEWAY_TENANT_BY_KEY", None)


def test_auth_session_login_with_admin_key_supports_superadmin_session(gateway_with_sqlite):
    client = gateway_with_sqlite
    os.environ["HG_GATEWAY_ADMIN_KEY"] = "root-key"
    try:
        login = client.post("/v1/auth/session/login", json={"admin_key": "root-key"})
        assert login.status_code == 200
        payload = login.json()
        assert "superadmin" in payload["roles"]

        me = client.get("/v1/auth/me", cookies=login.cookies)
        assert me.status_code == 200
        assert "superadmin" in me.json()["roles"]
    finally:
        os.environ.pop("HG_GATEWAY_ADMIN_KEY", None)


def test_browser_operator_session_sees_unassigned_approvals(gateway_with_sqlite):
    client = gateway_with_sqlite
    os.environ["HG_GATEWAY_API_KEY"] = "op-test-key"
    os.environ["HG_GATEWAY_TENANT_BY_KEY"] = "op-test-key:tenant-r2"
    try:
        from hg_gateway.store import get_store

        store = get_store()
        approval_id = store.approval_add(
            "tenant-r2",
            kind="tool_use",
            title="Approve tool action",
            summary="Needs operator review",
            risk="high",
            requested_by="agent-runtime",
            payload={"note": "demo"},
        )

        login = client.post("/v1/auth/session/login", json={"operator_key": "op-test-key"})
        assert login.status_code == 200
        assert "operator" in login.json()["roles"]

        response = client.get("/v1/approvals", cookies=login.cookies)
        assert response.status_code == 200
        approvals = response.json()["approvals"]
        assert any(item["id"] == approval_id for item in approvals)
    finally:
        os.environ.pop("HG_GATEWAY_API_KEY", None)
        os.environ.pop("HG_GATEWAY_TENANT_BY_KEY", None)


def test_browser_principal_session_only_sees_assigned_approvals(gateway_with_sqlite):
    client = gateway_with_sqlite
    os.environ["HG_GATEWAY_PRINCIPAL_KEYS"] = "principal-test:tenant-p:principal-1"
    try:
        from hg_gateway.store import get_store

        store = get_store()
        visible_id = store.approval_add(
            "tenant-p",
            kind="tool_use",
            title="Assigned approval",
            summary="Visible to principal",
            risk="medium",
            requested_by="agent-runtime",
            payload={"note": "assigned"},
            assigned_principal_id="principal-1",
        )
        store.approval_add(
            "tenant-p",
            kind="tool_use",
            title="Unassigned approval",
            summary="Should stay hidden",
            risk="medium",
            requested_by="agent-runtime",
            payload={"note": "hidden"},
        )

        login = client.post("/v1/auth/session/login", json={"operator_key": "principal-test"})
        assert login.status_code == 200
        assert login.json()["roles"] == ["principal"]

        response = client.get("/v1/approvals", cookies=login.cookies)
        assert response.status_code == 200
        approvals = response.json()["approvals"]
        assert [item["id"] for item in approvals] == [visible_id]
    finally:
        os.environ.pop("HG_GATEWAY_PRINCIPAL_KEYS", None)


def test_scim_requires_api_key(gateway_with_sqlite):
    """SCIM endpoints require X-API-Key; without it, 403."""
    client = gateway_with_sqlite
    r = client.get("/scim/v2/Users")
    assert r.status_code in (401, 403)


def test_scim_users_list_with_key(gateway_with_sqlite):
    """With valid API key, SCIM Users returns list (empty)."""
    client = gateway_with_sqlite
    os.environ["HG_GATEWAY_API_KEY"] = "test-key"
    os.environ["HG_GATEWAY_TENANT_BY_KEY"] = "test-key:default"
    try:
        r = client.get("/scim/v2/Users", headers={"X-API-Key": "test-key"})
        assert r.status_code == 200
        data = r.json()
        assert "Resources" in data
        assert "totalResults" in data
    finally:
        os.environ.pop("HG_GATEWAY_API_KEY", None)
        os.environ.pop("HG_GATEWAY_TENANT_BY_KEY", None)


def test_scim_create_user_and_list(gateway_with_sqlite):
    """Create user via SCIM (tenant_admin key), then list and get."""
    client = gateway_with_sqlite
    os.environ["HG_GATEWAY_API_KEY"] = "scim-test-key"
    os.environ["HG_GATEWAY_TENANT_BY_KEY"] = "scim-test-key:tenant1"
    os.environ["HG_GATEWAY_TENANT_ADMIN_KEYS"] = "scim-test-key"
    try:
        r = client.post(
            "/scim/v2/Users",
            headers={"X-API-Key": "scim-test-key", "Content-Type": "application/json"},
            json={"userName": "alice", "displayName": "Alice", "active": True},
        )
        assert r.status_code == 200
        body = r.json()
        assert "id" in body
        assert body["userName"] == "alice"
        uid = body["id"]
        r2 = client.get("/scim/v2/Users", headers={"X-API-Key": "scim-test-key"})
        assert r2.status_code == 200
        assert any(u.get("userName") == "alice" for u in r2.json().get("Resources", []))
        r3 = client.get(f"/scim/v2/Users/{uid}", headers={"X-API-Key": "scim-test-key"})
        assert r3.status_code == 200
        assert r3.json()["userName"] == "alice"
    finally:
        os.environ.pop("HG_GATEWAY_API_KEY", None)
        os.environ.pop("HG_GATEWAY_TENANT_BY_KEY", None)
        os.environ.pop("HG_GATEWAY_TENANT_ADMIN_KEYS", None)


def test_scim_create_user_denied_without_tenant_admin(gateway_with_sqlite):
    """RBAC: operator key (not tenant_admin) cannot create user; 403."""
    client = gateway_with_sqlite
    os.environ["HG_GATEWAY_API_KEY"] = "viewer-key"
    os.environ["HG_GATEWAY_TENANT_BY_KEY"] = "viewer-key:tenant1"
    # Do NOT set TENANT_ADMIN_KEYS so viewer-key gets role operator
    try:
        r = client.post(
            "/scim/v2/Users",
            headers={"X-API-Key": "viewer-key", "Content-Type": "application/json"},
            json={"userName": "bob", "displayName": "Bob", "active": True},
        )
        assert r.status_code == 403
    finally:
        os.environ.pop("HG_GATEWAY_API_KEY", None)
        os.environ.pop("HG_GATEWAY_TENANT_BY_KEY", None)


def test_scim_groups_list_and_create(gateway_with_sqlite):
    """SCIM Groups list and create (tenant_admin key)."""
    client = gateway_with_sqlite
    os.environ["HG_GATEWAY_API_KEY"] = "scim-grp-key"
    os.environ["HG_GATEWAY_TENANT_BY_KEY"] = "scim-grp-key:tenant1"
    os.environ["HG_GATEWAY_TENANT_ADMIN_KEYS"] = "scim-grp-key"
    try:
        r = client.get("/scim/v2/Groups", headers={"X-API-Key": "scim-grp-key"})
        assert r.status_code == 200
        r = client.post(
            "/scim/v2/Groups",
            headers={"X-API-Key": "scim-grp-key", "Content-Type": "application/json"},
            json={"displayName": "admins"},
        )
        assert r.status_code == 200
        assert r.json()["displayName"] == "admins"
    finally:
        os.environ.pop("HG_GATEWAY_API_KEY", None)
        os.environ.pop("HG_GATEWAY_TENANT_BY_KEY", None)
        os.environ.pop("HG_GATEWAY_TENANT_ADMIN_KEYS", None)
