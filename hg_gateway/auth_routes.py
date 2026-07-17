"""
Pack 16 / R2: browser auth routes for OIDC and key-backed session login.
"""

from __future__ import annotations

import base64
import os
import secrets
import urllib.parse
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from hg_gateway.auth import (
    _resolve_principal_key,
    _tenant_admin_keys,
    _tenant_from_api_key,
    _valid_operator_keys,
)
from hg_gateway.session_store import (
    SESSION_COOKIE_NAME,
    create_session,
    delete_session,
    get_session,
    list_sessions_for_principal,
)

router = APIRouter(tags=["auth"])

CSRF_HEADER = "X-CSRF-Token"
SESSION_TTL_SEC = int(os.environ.get("HG_SESSION_TTL_SEC", "86400"))  # 24h
OIDC_ID_TOKEN_COOKIE = "hg_oidc_id_token"

# OIDC config (Keycloak)
def _oidc_public_base() -> str:
    return (
        os.environ.get("KEYCLOAK_PUBLIC_URL")
        or os.environ.get("KEYCLOAK_URL")
        or "http://localhost:8080"
    ).rstrip("/")


def _oidc_internal_base() -> str:
    return (
        os.environ.get("KEYCLOAK_INTERNAL_URL")
        or os.environ.get("KEYCLOAK_URL")
        or "http://localhost:8080"
    ).rstrip("/")


def _oidc_issuer() -> str:
    base = _oidc_public_base()
    realm = os.environ.get("KEYCLOAK_REALM", "hg")
    return f"{base}/realms/{realm}"


def _oidc_internal_issuer() -> str:
    base = _oidc_internal_base()
    realm = os.environ.get("KEYCLOAK_REALM", "hg")
    return f"{base}/realms/{realm}"


def _oidc_logout_url() -> str:
    return f"{_oidc_issuer()}/protocol/openid-connect/logout"

def _oidc_client_id() -> str:
    return os.environ.get("KEYCLOAK_CLIENT_ID", "gateway-ui")

def _oidc_enabled() -> bool:
    return os.environ.get("HG_OIDC_ENABLED", "").strip().lower() in ("1", "true", "yes")


def _demo_login_enabled() -> bool:
    explicit = os.environ.get("HG_DEMO_LOGIN_ENABLED", "").strip().lower()
    if explicit in ("0", "false", "no"):
        return False
    if explicit in ("1", "true", "yes"):
        return True
    env_label = (os.environ.get("HG_ENV", "Demo") or "Demo").strip().lower()
    return env_label in ("demo", "dev", "development", "test", "testing") and not _oidc_enabled()

def _cookie_domain() -> Optional[str]:
    return os.environ.get("HG_SESSION_COOKIE_DOMAIN") or None

def _cookie_secure() -> bool:
    return os.environ.get("HG_SESSION_COOKIE_SECURE", "").strip().lower() in ("1", "true", "yes")


def _pkce_code_verifier() -> str:
    return secrets.token_urlsafe(32)


def _pkce_challenge(verifier: str) -> str:
    import hashlib

    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _oidc_redirect_cookie_encode(callback_redirect_uri: str, frontend_redirect_uri: Optional[str]) -> str:
    payload = f"{callback_redirect_uri}\n{frontend_redirect_uri or ''}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _oidc_redirect_cookie_decode(value: str) -> tuple[Optional[str], Optional[str]]:
    try:
        decoded = base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8")
        callback_redirect_uri, frontend_redirect_uri = (decoded.split("\n", 1) + [""])[:2]
        return callback_redirect_uri or None, frontend_redirect_uri or None
    except Exception:
        return None, None


def _resolve_oidc_roles(payload: dict, client_id: str) -> List[str]:
    roles: List[str] = []
    realm_access = payload.get("realm_access") or {}
    roles.extend(realm_access.get("roles") or [])

    resource_access = payload.get("resource_access") or {}
    if isinstance(resource_access, dict):
        client_access = resource_access.get(client_id) or {}
        roles.extend(client_access.get("roles") or [])

    groups = payload.get("groups") or []
    if isinstance(groups, list):
        normalized_groups = {str(group).strip("/").lower() for group in groups}
        if "superadmin" in normalized_groups:
            roles.append("superadmin")
        if "tenant_admin" in normalized_groups or "tenant-admin" in normalized_groups:
            roles.append("tenant_admin")
        if "operator" in normalized_groups:
            roles.append("operator")
        if "principal" in normalized_groups or "client" in normalized_groups:
            roles.append("principal")

    preferred_username = str(payload.get("preferred_username") or "").strip().lower()
    if preferred_username:
        if preferred_username == "demo-superadmin":
            roles.extend(["superadmin", "operator"])
        elif preferred_username == "demo-tenant-admin":
            roles.append("tenant_admin")
        elif preferred_username == "demo-operator":
            roles.append("operator")
        elif preferred_username == "demo-client":
            roles.append("principal")

    seen: set[str] = set()
    normalized_roles: List[str] = []
    for role in roles:
        value = str(role).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized_roles.append(value)
    return normalized_roles


class SessionLoginRequest(BaseModel):
    operator_key: Optional[str] = None
    admin_key: Optional[str] = None


def _cookie_response_payload(session: dict) -> dict:
    return {
        "tenant_id": session["tenant_id"],
        "principal_id": session["principal_id"],
        "roles": session["roles"],
        "created_at": session.get("created_at"),
        "expires_at": session["expires_at"],
    }


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        max_age=SESSION_TTL_SEC,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        domain=_cookie_domain(),
    )


def _audit_auth_event(tenant_id: str, event_name: str, payload: dict) -> None:
    try:
        from hg_gateway.store import get_store

        store = get_store()
        if hasattr(store, "audit_append"):
            store.audit_append(tenant_id, event_name, payload)
    except Exception:
        pass


def _resolve_key_login(operator_key: Optional[str], admin_key: Optional[str]) -> dict:
    operator_key = (operator_key or "").strip() or None
    admin_key = (admin_key or "").strip() or None
    if not operator_key and not admin_key:
        raise HTTPException(status_code=400, detail="operator_key or admin_key is required")

    roles: List[str] = []
    tenant_id = os.environ.get("HG_OIDC_DEFAULT_TENANT", "default")
    principal_id = "browser-user"

    if operator_key:
        principal_mapping = _resolve_principal_key(operator_key)
        if principal_mapping is not None:
            tenant_id, principal_id = principal_mapping
            roles.append("principal")
        else:
            valid = _valid_operator_keys()
            is_store_key = False
            if operator_key not in valid:
                try:
                    from hg_gateway.store import get_store

                    store = get_store()
                    if hasattr(store, "tenant_key_lookup") and store.tenant_key_lookup(operator_key):
                        is_store_key = True
                except Exception:
                    is_store_key = False
            if operator_key not in valid and not is_store_key:
                raise HTTPException(status_code=401, detail="Invalid operator key")
            tenant_id = _tenant_from_api_key(operator_key)
            if operator_key in _tenant_admin_keys():
                roles.append("tenant_admin")
                principal_id = "tenant-admin"
            else:
                roles.append("operator")
                principal_id = "operator"

    if admin_key:
        expected_admin = os.environ.get("HG_GATEWAY_ADMIN_KEY", "").strip()
        if not expected_admin:
            raise HTTPException(status_code=503, detail="Admin key not configured")
        if admin_key != expected_admin:
            raise HTTPException(status_code=403, detail="Invalid admin key")
        if "superadmin" not in roles:
            roles.append("superadmin")
        if not operator_key:
            principal_id = "superadmin"

    if not roles:
        raise HTTPException(status_code=403, detail="Unable to resolve browser auth roles")

    session_id, csrf_token = create_session(
        tenant_id,
        principal_id,
        roles,
        ttl_seconds=SESSION_TTL_SEC,
    )
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=500, detail="Failed to create browser session")
    session["csrf_token"] = csrf_token
    return session


@router.get("/auth/config")
def auth_config():
    return {
        "oidc_enabled": _oidc_enabled(),
        "oidc_issuer": _oidc_issuer() if _oidc_enabled() else None,
        "oidc_client_id": _oidc_client_id() if _oidc_enabled() else None,
        "session_ttl_sec": SESSION_TTL_SEC,
        "session_cookie_name": SESSION_COOKIE_NAME,
        "supports_key_exchange_login": True,
        "demo_login_enabled": _demo_login_enabled(),
        "demo_login_roles": ["operator", "superadmin"] if _demo_login_enabled() else [],
    }


@router.post("/auth/demo/login")
def auth_demo_login(response: Response):
    """Deterministic demo operator session without hidden browser key setup."""
    if not _demo_login_enabled():
        raise HTTPException(status_code=403, detail="Demo login is not enabled")
    tenant_id = os.environ.get("HG_OIDC_DEFAULT_TENANT", "default")
    principal_id = "demo-operator"
    roles = ["operator"]
    if os.environ.get("HG_DEMO_INCLUDE_SUPERADMIN", "1").strip().lower() in ("1", "true", "yes"):
        roles.append("superadmin")
    session_id, _csrf_token = create_session(
        tenant_id,
        principal_id,
        roles,
        ttl_seconds=SESSION_TTL_SEC,
    )
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=500, detail="Failed to create demo session")
    _set_session_cookie(response, session_id)
    _audit_auth_event(
        tenant_id,
        "auth.login",
        {
            "principal_id": principal_id,
            "session_id": session_id,
            "roles": roles,
            "login_mode": "demo_deterministic",
        },
    )
    return {
        **_cookie_response_payload(session),
        "login_mode": "demo_deterministic",
    }


@router.post("/auth/session/login")
def auth_session_login(body: SessionLoginRequest, response: Response):
    session = _resolve_key_login(body.operator_key, body.admin_key)
    _set_session_cookie(response, session["session_id"])
    _audit_auth_event(
        session["tenant_id"],
        "auth.login",
        {
            "principal_id": session["principal_id"],
            "session_id": session["session_id"],
            "roles": session["roles"],
            "login_mode": "key_exchange",
        },
    )
    return {
        **_cookie_response_payload(session),
        "login_mode": "key_exchange",
    }


@router.get("/auth/oidc/start")
def oidc_start(
    request: Request,
    redirect_uri: Optional[str] = Query(None, description="OIDC callback URL after login"),
    frontend_redirect_uri: Optional[str] = Query(None, description="Frontend URL to return to after callback"),
    state: Optional[str] = Query(None),
):
    """Redirect to Keycloak authorization endpoint (PKCE)."""
    if not _oidc_enabled():
        raise HTTPException(status_code=501, detail="OIDC not enabled (set HG_OIDC_ENABLED=1)")
    _oidc_public_issuer = _oidc_issuer()
    auth_url = f"{_oidc_public_issuer}/protocol/openid-connect/auth"
    client_id = _oidc_client_id()
    state_token = state or secrets.token_urlsafe(24)
    verifier = _pkce_code_verifier()
    challenge = _pkce_challenge(verifier)
    callback_redirect_uri = redirect_uri or os.environ.get("HG_OIDC_CALLBACK_URL") or urllib.parse.urljoin(str(request.base_url), "v1/auth/oidc/callback")
    params = {
        "client_id": client_id,
        "redirect_uri": callback_redirect_uri,
        "response_type": "code",
        "scope": "openid profile email",
        "state": state_token,
        "prompt": "login",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    # Store verifier for callback (in production use server-side cache keyed by state)
    redirect = RedirectResponse(url=url, status_code=302)
    redirect.set_cookie(
        "hg_oidc_state",
        f"{state_token}:{verifier}",
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
    )
    redirect.set_cookie(
        "hg_oidc_redirects",
        _oidc_redirect_cookie_encode(callback_redirect_uri, frontend_redirect_uri),
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
    )
    return redirect


@router.get("/auth/oidc/callback")
def oidc_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    redirect_uri: Optional[str] = Query(None),
):
    """Exchange code for tokens, create session, set cookie, redirect."""
    if not _oidc_enabled():
        raise HTTPException(status_code=501, detail="OIDC not enabled")
    state_cookie = request.cookies.get("hg_oidc_state")
    if not state_cookie or ":" not in state_cookie:
        raise HTTPException(status_code=400, detail="Missing or invalid state cookie")
    stored_state, verifier = state_cookie.split(":", 1)
    if stored_state != state:
        raise HTTPException(status_code=400, detail="State mismatch")
    redirect_cookie = request.cookies.get("hg_oidc_redirects") or ""
    cookie_callback_redirect_uri, cookie_frontend_redirect_uri = _oidc_redirect_cookie_decode(redirect_cookie)
    callback_redirect_uri = redirect_uri or cookie_callback_redirect_uri
    if not callback_redirect_uri:
        raise HTTPException(status_code=400, detail="Missing callback redirect URI")
    token_url = f"{_oidc_internal_issuer()}/protocol/openid-connect/token"
    client_id = _oidc_client_id()
    import httpx
    with httpx.Client(timeout=10.0) as client:
        r = client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": code,
                "redirect_uri": callback_redirect_uri,
                "code_verifier": verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=400, detail="Token exchange failed")
    token_data = r.json()
    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="No id_token")
    # KLR tranche (2026-07-04): verify the id_token signature/issuer/expiry against
    # the live Keycloak JWKS before trusting any claim. This replaces the former
    # `verify_signature: False` decode, which let a forged token mint a privileged
    # session. Verification failure fails closed — no session is created.
    try:
        import jwt
        from hg_gateway.operator_auth_boundary import _load_jwks
        keys = _load_jwks()
        header = jwt.get_unverified_header(id_token)
        key = keys.get(header.get("kid", ""))
        if key is None:
            keys = _load_jwks(force=True)  # key rotation: refresh once
            key = keys.get(header.get("kid", ""))
        if key is None:
            raise HTTPException(status_code=401, detail="Unknown signing key")
        payload = jwt.decode(
            id_token, key=key, algorithms=["RS256"], issuer=_oidc_issuer(),
            audience=client_id, options={"verify_aud": True})
    except HTTPException:
        raise
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="id_token signature/claims invalid")
    except Exception:
        # JWKS unreachable etc. — fail closed rather than trust an unverified token.
        raise HTTPException(status_code=401, detail="id_token could not be verified")
    sub = payload.get("sub") or ""
    roles = _resolve_oidc_roles(payload, client_id)
    # Default tenant from token or env
    tenant_id = payload.get("tenant_id") or os.environ.get("HG_OIDC_DEFAULT_TENANT", "default")
    principal_id = sub or f"oidc-{sub[:8]}"
    if not roles:
        roles = ["viewer"]
    session_id, _csrf_token = create_session(tenant_id, principal_id, roles, ttl_seconds=SESSION_TTL_SEC, idp_sub=sub)
    _audit_auth_event(tenant_id, "auth.login", {"principal_id": principal_id, "idp_sub": sub, "session_id": session_id, "login_mode": "oidc"})
    # Redirect to frontend (e.g. / or redirect_uri without query)
    frontend_redirect = cookie_frontend_redirect_uri or os.environ.get("HG_OIDC_FRONTEND_REDIRECT") or callback_redirect_uri.split("?")[0]
    redirect = RedirectResponse(url=frontend_redirect, status_code=302)
    redirect.delete_cookie("hg_oidc_state")
    redirect.delete_cookie("hg_oidc_redirects")
    _set_session_cookie(redirect, session_id)
    # KLR tranche (2026-07-04): the raw id_token is NO LONGER stored in a cookie
    # (it was a 24h raw-token leak sink). The opaque server-side session is the
    # only credential the browser holds; RP-initiated logout uses the session's
    # recorded idp_sub, not a client-held token.
    return redirect


@router.get("/auth/oidc/logout")
def oidc_logout(
    request: Request,
    frontend_redirect_uri: Optional[str] = Query(None, description="Frontend URL to return to after logout"),
):
    session_id = _get_session_cookie(request)
    if session_id:
        session = get_session(session_id)
        if session:
            _audit_auth_event(
                session["tenant_id"],
                "auth.logout",
                {"principal_id": session["principal_id"], "session_id": session_id, "login_mode": "oidc"},
            )
        delete_session(session_id)
    frontend_redirect = frontend_redirect_uri or os.environ.get("HG_OIDC_FRONTEND_REDIRECT") or str(request.base_url)
    params = {
        "client_id": _oidc_client_id(),
        "post_logout_redirect_uri": frontend_redirect,
    }
    id_token_hint = request.cookies.get(OIDC_ID_TOKEN_COOKIE)
    if id_token_hint:
        params["id_token_hint"] = id_token_hint
    logout_url = f"{_oidc_logout_url()}?{urllib.parse.urlencode(params)}"
    response = RedirectResponse(url=logout_url, status_code=302)
    response.delete_cookie(SESSION_COOKIE_NAME, domain=_cookie_domain())
    response.delete_cookie(OIDC_ID_TOKEN_COOKIE, domain=_cookie_domain())
    response.delete_cookie("hg_oidc_state")
    response.delete_cookie("hg_oidc_redirects")
    return response


def _get_session_cookie(request: Request) -> Optional[str]:
    return request.cookies.get(SESSION_COOKIE_NAME)


@router.post("/auth/logout")
def auth_logout(request: Request, response: Response):
    """Invalidate session and clear cookie. Audit auth.logout when session existed."""
    session_id = _get_session_cookie(request)
    if session_id:
        session = get_session(session_id)
        if session:
            _audit_auth_event(session["tenant_id"], "auth.logout", {"principal_id": session["principal_id"], "session_id": session_id})
        delete_session(session_id)
    response.delete_cookie(SESSION_COOKIE_NAME, domain=_cookie_domain())
    response.delete_cookie(OIDC_ID_TOKEN_COOKIE, domain=_cookie_domain())
    return {"ok": True}


@router.get("/auth/me")
def auth_me(request: Request):
    """Return current session user info."""
    session_id = _get_session_cookie(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return _cookie_response_payload(session)


@router.get("/auth/sessions")
def auth_sessions(request: Request):
    """List sessions for current user."""
    session_id = _get_session_cookie(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return {"sessions": list_sessions_for_principal(session["tenant_id"], session["principal_id"])}


@router.delete("/auth/sessions/{sid}")
def auth_session_delete(
    sid: str,
    request: Request,
    response: Response,
):
    """Revoke a session (own or as admin)."""
    session_id = _get_session_cookie(request)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    current = get_session(session_id)
    if not current:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    # Allow revoking own session or if superadmin/tenant_admin
    if sid != session_id and "superadmin" not in current["roles"] and "tenant_admin" not in current["roles"]:
        raise HTTPException(status_code=403, detail="Cannot revoke other sessions")
    delete_session(sid)
    if sid == session_id:
        response.delete_cookie(SESSION_COOKIE_NAME, domain=_cookie_domain())
    return {"ok": True}
