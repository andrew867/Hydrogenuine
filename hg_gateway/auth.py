"""
Gateway auth: reject default key outside DEV; require API key for chat and approvals.
Pack3: tenant resolution from X-Tenant-ID or default.
Pack4: prod = tenant from API key only (HG_DEV_ALLOW_TENANT_HEADER=false); dev = X-Tenant-ID allowed.
Pack13: impersonation JWT (short-lived) for superadmin; Bearer token can be impersonation JWT.
Tenant-admin and principal: HG_GATEWAY_TENANT_ADMIN_KEYS, HG_GATEWAY_PRINCIPAL_KEYS (key:tenant_id:principal_id).
"""

import os
import time
from typing import Any, Dict, Optional, Set, Tuple

from fastapi import Header, HTTPException, Request

from hg_core.tenancy.context import TenantContext, DEFAULT_TENANT_CONTEXT
from hg_gateway.session_store import get_session

try:
    import jwt
except ImportError:
    jwt = None  # type: ignore


DEFAULT_KEY = "changeme"
DEFAULT_DEMO_API_KEY = "demo-api-key"
DEFAULT_DEMO_ADMIN_KEY = "demo-admin-key"
ENV_KEY = "HG_GATEWAY_API_KEY"
AUTH_MODE_ENV = "HG_GATEWAY_AUTH_MODE"
DEV_ENV = "HG_GATEWAY_DEV"
RUNTIME_ENV = "HG_ENV"
TENANT_HEADER = "X-Tenant-ID"
# Pack4: when false (prod), tenant_id is derived only from API key; X-Tenant-ID is ignored.
TENANT_HEADER_ALLOWED_ENV = "HG_DEV_ALLOW_TENANT_HEADER"
# Pack4: optional mapping "key1:tenant_a,key2:tenant_b"; if unset, valid key maps to tenant "default".
TENANT_BY_KEY_ENV = "HG_GATEWAY_TENANT_BY_KEY"
# Tenant-admin: comma-separated keys; these get role tenant_admin for their tenant.
TENANT_ADMIN_KEYS_ENV = "HG_GATEWAY_TENANT_ADMIN_KEYS"
# Principal keys: "key1:tenant_id:principal_id,key2:tenant_id:principal_id"; key resolves to that tenant and principal.
PRINCIPAL_KEYS_ENV = "HG_GATEWAY_PRINCIPAL_KEYS"


def _is_dev() -> bool:
    return os.environ.get(DEV_ENV, "").strip().lower() in ("1", "true", "yes")


def _runtime_env_label() -> str:
    return (os.environ.get(RUNTIME_ENV, "Demo") or "Demo").strip()


def _strict_auth_required() -> bool:
    return _runtime_env_label().lower() not in {"demo", "dev", "development", "test", "testing"} and not _is_dev()


def _auth_mode() -> str:
    return (os.environ.get(AUTH_MODE_ENV) or "api-key").strip().lower()


def _request_is_loopback(request: Request) -> bool:
    client = getattr(request, "client", None)
    host = str(getattr(client, "host", "") or "").strip().lower()
    return host in {"127.0.0.1", "::1", "localhost", "testclient"}


def _allow_tenant_header() -> bool:
    """When true (dev), X-Tenant-ID header may override tenant. When false (prod), tenant from key only."""
    return os.environ.get(TENANT_HEADER_ALLOWED_ENV, "").strip().lower() in ("1", "true", "yes")


def _tenant_from_api_key(api_key: str) -> str:
    """
    Resolve tenant_id from API key. Uses HG_GATEWAY_TENANT_BY_KEY (key1:tenant_a,key2:tenant_b).
    Pack 13: Then tries store.tenant_key_lookup(api_key) for DB-stored tenant keys.
    If key not in map, returns 'default'.
    """
    raw = os.environ.get(TENANT_BY_KEY_ENV, "").strip()
    if raw:
        for part in raw.split(","):
            part = part.strip()
            if ":" in part:
                k, tid = part.split(":", 1)
                if k.strip() == api_key:
                    return tid.strip() or "default"
    try:
        from hg_gateway.store import get_store
        store = get_store()
        if hasattr(store, "tenant_key_lookup"):
            tid = store.tenant_key_lookup(api_key)
            if tid:
                return tid
    except Exception:
        pass
    return DEFAULT_TENANT_CONTEXT.tenant_id


def _get_expected_key() -> str:
    return os.environ.get(ENV_KEY, DEFAULT_KEY).strip() or DEFAULT_KEY


def _looks_like_default_key(value: str, *, admin: bool = False) -> bool:
    normalized = (value or "").strip()
    defaults = {DEFAULT_KEY}
    if admin:
        defaults.add(DEFAULT_DEMO_ADMIN_KEY)
    else:
        defaults.add(DEFAULT_DEMO_API_KEY)
    return normalized in defaults or not normalized


def runtime_auth_diagnostics() -> Dict[str, Any]:
    expected = _get_expected_key()
    admin_key = os.environ.get(ADMIN_KEY_ENV, "").strip()
    return {
        "env": _runtime_env_label(),
        "auth_mode": _auth_mode(),
        "gateway_dev": _is_dev(),
        "strict_auth_required": _strict_auth_required(),
        "api_key_configured": bool(expected),
        "api_key_uses_default": _looks_like_default_key(expected),
        "admin_key_configured": bool(admin_key),
        "admin_key_uses_default": _looks_like_default_key(admin_key, admin=True),
        "tenant_header_allowed": _allow_tenant_header(),
    }


def validate_runtime_auth_config() -> None:
    if _auth_mode() == "local-no-key" and _strict_auth_required():
        raise RuntimeError(
            "Gateway refuses local-no-key authentication outside demo/development mode. "
            "Set HG_GATEWAY_AUTH_MODE=api-key and configure gateway credentials."
        )
    if not _strict_auth_required():
        return
    expected = _get_expected_key()
    admin_key = os.environ.get(ADMIN_KEY_ENV, "").strip()
    if _looks_like_default_key(expected):
        raise RuntimeError(
            "Gateway refuses to start in non-demo mode with a default or missing HG_GATEWAY_API_KEY."
        )
    if _looks_like_default_key(admin_key, admin=True):
        raise RuntimeError(
            "Gateway refuses to start in non-demo mode with a default or missing HG_GATEWAY_ADMIN_KEY."
        )


def runtime_safety_diagnostics() -> Dict[str, Any]:
    from hg_gateway.tools import get_runtime_diagnostics
    from hg_core.ledger import crypto as ledger_crypto

    tool_runtime = get_runtime_diagnostics()
    ledger_crypto_mode = "ed25519" if getattr(ledger_crypto, "_NACL", False) else "stub"
    return {
        "env": _runtime_env_label(),
        "strict_runtime_safety_required": _strict_auth_required(),
        "tool_runtime": tool_runtime,
        "tool_stub_fallback_active": bool(tool_runtime.get("stub_fallback_active")),
        "ledger_crypto_mode": ledger_crypto_mode,
        "ledger_crypto_stub_active": ledger_crypto_mode == "stub",
    }


def validate_runtime_safety_config() -> None:
    if not _strict_auth_required():
        return
    diag = runtime_safety_diagnostics()
    errors = []
    if diag.get("tool_stub_fallback_active"):
        tool_runtime = diag.get("tool_runtime") or {}
        build_error = tool_runtime.get("build_error") or "unknown error"
        errors.append(
            "Gateway refuses to start in non-demo mode with stub tool adapter fallback active. "
            f"build_error={build_error}. Ensure hg_core.task_graph.tool_contract_setup.build_default_tool_contract "
            "loads successfully and that the real tool contract dependencies are installed."
        )
    if diag.get("ledger_crypto_stub_active"):
        errors.append(
            "Gateway refuses to start in non-demo mode with stub ledger crypto. "
            "Install pynacl and configure real ledger signing keys before starting production-like environments."
        )
    if errors:
        raise RuntimeError(" ".join(errors))


def _valid_operator_keys() -> Set[str]:
    """Set of keys that are valid as operator keys (single ENV_KEY + all keys from TENANT_BY_KEY)."""
    keys: Set[str] = set()
    single = _get_expected_key()
    if single:
        keys.add(single)
    raw = os.environ.get(TENANT_BY_KEY_ENV, "").strip()
    for part in raw.split(","):
        part = part.strip()
        if ":" in part:
            k = part.split(":", 1)[0].strip()
            if k:
                keys.add(k)
    return keys


def _principal_keys_mapping() -> list[Tuple[str, str, str]]:
    """List of (key, tenant_id, principal_id) from HG_GATEWAY_PRINCIPAL_KEYS (key:tenant_id:principal_id,...)."""
    out: list[Tuple[str, str, str]] = []
    raw = os.environ.get(PRINCIPAL_KEYS_ENV, "").strip()
    for part in raw.split(","):
        part = part.strip()
        if part.count(":") >= 2:
            # key:tenant_id:principal_id (principal_id may contain colons)
            first, rest = part.split(":", 1)
            if ":" in rest:
                tid, pid = rest.split(":", 1)
                out.append((first.strip(), tid.strip(), pid.strip()))
    return out


def _tenant_admin_keys() -> Set[str]:
    """Set of keys that have tenant_admin role for their tenant."""
    keys: Set[str] = set()
    raw = os.environ.get(TENANT_ADMIN_KEYS_ENV, "").strip()
    for k in raw.split(","):
        k = k.strip()
        if k:
            keys.add(k)
    return keys


def _resolve_principal_key(api_key: str) -> Optional[Tuple[str, str]]:
    """If api_key is a principal key, return (tenant_id, principal_id); else None."""
    for k, tid, pid in _principal_keys_mapping():
        if k == api_key:
            return (tid or "default", pid)
    return None


def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None),
) -> None:
    """
    Dependency: require valid API key or valid impersonation JWT. Reject default 'changeme' outside DEV.
    Accepts X-API-Key header or Authorization: Bearer <key or impersonation JWT>.
    If Bearer token decodes as impersonation JWT, sets request.state.impersonation and request.state.api_key = __impersonation__.
    Otherwise valid keys: single HG_GATEWAY_API_KEY, any key in HG_GATEWAY_TENANT_BY_KEY, or any key in HG_GATEWAY_PRINCIPAL_KEYS.
    Sets request.state.api_key for tenant/role resolution.
    """
    if _auth_mode() == "local-no-key":
        if not _request_is_loopback(request):
            raise HTTPException(
                status_code=403,
                detail=(
                    "Local no-key mode accepts loopback requests only. "
                    "Use API-key mode before exposing the gateway beyond this machine."
                ),
            )
        request.state.api_key = "__local__"
        request.state.role = "operator"
        return

    path = (getattr(request, "url", None).path if getattr(request, "url", None) is not None else "") or ""
    admin_candidate = (x_admin_key or "").strip()
    expected_admin = os.environ.get(ADMIN_KEY_ENV, "").strip()
    if path.startswith("/v1/admin/") and admin_candidate and expected_admin and admin_candidate == expected_admin:
        request.state.api_key = "__admin__"
        request.state.role = "superadmin"
        return

    key = None
    bearer_token = None
    if x_api_key:
        key = x_api_key.strip()
    elif authorization and authorization.strip().lower().startswith("bearer "):
        bearer_token = authorization.strip()[7:].strip()
        key = bearer_token

    if path.startswith("/v1/admin/") and key and expected_admin and key == expected_admin:
        request.state.api_key = "__admin__"
        request.state.role = "superadmin"
        return

    if not key:
        session_id = request.cookies.get("hg_session")
        if session_id:
            session = get_session(session_id)
            if session:
                request.state.api_key = "__session__"
                request.state.principal_id = session["principal_id"]
                request.state.role = session["roles"][0] if session["roles"] else "viewer"
                request.state.browser_session = session
                return
        raise HTTPException(status_code=401, detail="Missing X-API-Key or Authorization: Bearer")

    # Pack 13: Try Bearer token as impersonation JWT first
    if bearer_token is not None:
        imp = decode_impersonation_token(bearer_token)
        if imp is not None:
            request.state.impersonation = imp
            request.state.api_key = "__impersonation__"
            return

    valid = _valid_operator_keys() | {t[0] for t in _principal_keys_mapping()}
    if key not in valid:
        try:
            from hg_gateway.store import get_store
            store = get_store()
            if hasattr(store, "tenant_key_lookup") and store.tenant_key_lookup(key):
                request.state.api_key = key
                return
        except Exception:
            pass
        raise HTTPException(
            status_code=401,
            detail=(
                "Local gateway credential rejected. This credential protects the local HTTP gateway; "
                "it is not a model-provider API key. Run 'hg doctor' and check HG_GATEWAY_API_KEY."
            ),
        )
    if key == DEFAULT_KEY and not _is_dev():
        raise HTTPException(
            status_code=401,
            detail="Default API key not allowed outside DEV; set HG_GATEWAY_API_KEY and HG_GATEWAY_DEV=0",
        )
    request.state.api_key = key


ADMIN_KEY_ENV = "HG_GATEWAY_ADMIN_KEY"

# Pack 13: Impersonation JWT (short-lived). Secret from HG_IMPERSONATION_JWT_SECRET or HG_GATEWAY_ADMIN_KEY.
IMPERSONATION_JWT_SECRET_ENV = "HG_IMPERSONATION_JWT_SECRET"
IMPERSONATION_JWT_ALGORITHM = "HS256"
IMPERSONATION_JWT_EXPIRES_SECONDS = 3600  # 1 hour


def _impersonation_jwt_secret() -> str:
    secret = os.environ.get(IMPERSONATION_JWT_SECRET_ENV, "").strip()
    if secret:
        return secret
    return os.environ.get(ADMIN_KEY_ENV, "").strip() or "impersonation-secret-change-me"


def create_impersonation_token(tenant_id: str, role: str) -> Tuple[str, int]:
    """Pack 13: Create short-lived JWT for impersonation. Returns (token, expires_at_epoch)."""
    if not jwt:
        raise HTTPException(status_code=503, detail="PyJWT not available")
    now = int(time.time())
    exp = now + IMPERSONATION_JWT_EXPIRES_SECONDS
    payload = {"tenant_id": tenant_id, "role": role, "iat": now, "exp": exp, "sub": "impersonation"}
    token = jwt.encode(
        payload,
        _impersonation_jwt_secret(),
        algorithm=IMPERSONATION_JWT_ALGORITHM,
    )
    if hasattr(token, "decode"):
        token = token.decode("utf-8")
    return (token, exp)


def decode_impersonation_token(token: str) -> Optional[Dict[str, Any]]:
    """Pack 13: Decode and validate impersonation JWT. Returns payload dict or None if invalid."""
    if not jwt or not token or not token.strip():
        return None
    try:
        payload = jwt.decode(
            token.strip(),
            _impersonation_jwt_secret(),
            algorithms=[IMPERSONATION_JWT_ALGORITHM],
        )
        if payload.get("sub") != "impersonation" or "tenant_id" not in payload or "role" not in payload:
            return None
        return payload
    except Exception:
        return None


def verify_admin_key(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
) -> None:
    """Dependency: require X-Admin-Key header matching HG_GATEWAY_ADMIN_KEY (for tenant delete). Kept for backward compatibility."""
    expected = os.environ.get(ADMIN_KEY_ENV, "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Admin key not configured; set HG_GATEWAY_ADMIN_KEY in .env (or environment) and restart the gateway. "
            "For the operator UI Proof Run page, also build/serve with VITE_ADMIN_KEY set to the same value.",
        )
    key = (x_admin_key or "").strip()
    if key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key")


def require_admin(
    request: Request,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None),
) -> None:
    """Dependency: require admin key via X-Admin-Key OR Authorization: Bearer. Sets request.state.role = 'superadmin'."""
    session_id = request.cookies.get("hg_session")
    if session_id:
        session = get_session(session_id)
        if session and "superadmin" in (session.get("roles") or []):
            request.state.role = "superadmin"
            request.state.browser_session = session
            return
    expected = os.environ.get(ADMIN_KEY_ENV, "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Admin key not configured; set HG_GATEWAY_ADMIN_KEY in .env (or environment) and restart the gateway. "
            "For the operator UI Proof Run page, also build/serve with VITE_ADMIN_KEY set to the same value.",
        )
    key = (x_admin_key or "").strip()
    if not key and authorization and authorization.strip().lower().startswith("bearer "):
        key = authorization.strip()[7:].strip()
    if not key or key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Key")
    request.state.role = "superadmin"


def require_tenant_admin(request: Request) -> None:
    """Pack 13: Dependency: require role tenant_admin. Use for tenant-admin-only routes (e.g. principals CRUD)."""
    role = getattr(request.state, "role", None)
    if role != "tenant_admin":
        raise HTTPException(status_code=403, detail="tenant_admin role required")


def get_tenant_context(
    request: Request,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> TenantContext:
    """
    Dependency: resolve tenant and role. Impersonation JWT takes precedence, then principal key (fixed tenant + principal_id).
    Else tenant from TENANT_BY_KEY (or X-Tenant-ID in dev); role = tenant_admin if key in TENANT_ADMIN_KEYS else operator.
    Requires verify_api_key to have run (sets request.state.api_key and optionally request.state.impersonation).
    """
    browser_session = getattr(request.state, "browser_session", None)
    if browser_session is None:
        session_id = request.cookies.get("hg_session")
        if session_id:
            browser_session = get_session(session_id)
            if browser_session is not None:
                request.state.browser_session = browser_session
    if browser_session is not None:
        roles = browser_session.get("roles") or []
        request.state.principal_id = browser_session.get("principal_id")
        request.state.role = roles[0] if roles else "viewer"
        return TenantContext(
            tenant_id=browser_session.get("tenant_id") or "default",
            environment="prod" if not _is_dev() else "dev",
        )

    # Pack 13: Impersonation JWT — tenant and role from token only; ignore X-Tenant-ID
    imp = getattr(request.state, "impersonation", None)
    if imp is not None:
        request.state.principal_id = None
        request.state.role = imp.get("role") or "operator"
        return TenantContext(
            tenant_id=imp.get("tenant_id") or "default",
            environment="prod" if not _is_dev() else "dev",
        )

    api_key = getattr(request.state, "api_key", None) or ""
    principal_mapping = _resolve_principal_key(api_key)
    if principal_mapping is not None:
        tenant_id, principal_id = principal_mapping
        request.state.principal_id = principal_id
        request.state.role = "principal"
        return TenantContext(tenant_id=tenant_id or "default", environment="prod" if not _is_dev() else "dev")
    # Pack 13: In prod (HG_DEV_ALLOW_TENANT_HEADER not set), tenant is derived only from API key;
    # X-Tenant-ID is ignored to prevent header spoofing.
    if _allow_tenant_header():
        header_tenant = (x_tenant_id or "").strip()
        tenant_id = header_tenant if header_tenant else _tenant_from_api_key(api_key)
    else:
        tenant_id = _tenant_from_api_key(api_key)
    request.state.principal_id = None
    admin_keys = _tenant_admin_keys()
    if api_key in admin_keys:
        request.state.role = "tenant_admin"
    elif not _strict_auth_required() and _looks_like_default_key(api_key, admin=False):
        request.state.role = "tenant_admin"
    else:
        request.state.role = "operator"
    return TenantContext(tenant_id=tenant_id or "default", environment="prod" if not _is_dev() else "dev")
