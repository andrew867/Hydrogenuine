"""Ch4 Product API: RBAC (viewer, operator, admin). Deny by default."""

from fastapi import Header, HTTPException, Depends, Request

from .config import settings

# Role hierarchy: admin can do operator can do viewer
ROLE_ORDER = {"viewer": 0, "operator": 1, "admin": 2}


def _browser_session_product_role(request: Request) -> str | None:
    session_id = request.cookies.get("hg_session")
    if not session_id:
        return None
    try:
        from hg_gateway.session_store import get_session

        session = get_session(session_id)
    except Exception:
        return None
    if not session:
        return None
    roles = set(session.get("roles") or [])
    if "superadmin" in roles or "tenant_admin" in roles:
        return "admin"
    if "operator" in roles:
        return "operator"
    if roles & {"principal", "viewer"}:
        return "viewer"
    return None


def require_product_auth(request: Request, authorization: str = Header(default="")):
    """Resolve browser session or Bearer token to product role."""
    cookie_role = _browser_session_product_role(request)
    if cookie_role:
        return cookie_role
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token or browser session")
    key = parts[1]
    role = settings.product_api_keys.get(key)
    if not role:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return role


def require_product_role(min_role: str):
    """Dependency factory: require at least min_role (viewer, operator, admin)."""

    def _dep(role: str = Depends(require_product_auth)):
        if ROLE_ORDER.get(role, -1) < ROLE_ORDER.get(min_role, -1):
            raise HTTPException(status_code=403, detail="Insufficient role")
        return role

    return _dep
