from fastapi import Header, HTTPException, Query, Request
from .config import settings

def _browser_session_authenticated(request: Request) -> bool:
    session_id = request.cookies.get("hg_session")
    if not session_id:
        return False
    try:
        from hg_gateway.session_store import get_session

        session = get_session(session_id)
    except Exception:
        return False
    if not session:
        return False
    roles = set(session.get("roles") or [])
    return bool(roles & {"operator", "tenant_admin", "superadmin", "viewer"})


def require_api_key(request: Request, authorization: str = Header(default="")):
    if _browser_session_authenticated(request):
        return True
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")
    if parts[1] != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True


def require_api_key_or_query(
    request: Request,
    authorization: str = Header(default=""),
    api_key: str = Query(default="", alias="api_key"),
    stream_token: str = Query(default="", alias="stream_token"),
):
    """Allow auth via Bearer header, api_key query, browser session, or short-lived stream_token."""
    if _browser_session_authenticated(request):
        return True
    if stream_token:
        from ..services.stream_tokens import validate_stream_token

        run_id = request.path_params.get("run_id") if hasattr(request, "path_params") else None
        if run_id and validate_stream_token(stream_token, run_id):
            return True
    if api_key and api_key == settings.api_key:
        return True
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token or api_key")
    if parts[1] != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return True
