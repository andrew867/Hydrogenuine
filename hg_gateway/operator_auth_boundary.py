"""Gateway operator-decision auth boundary — verified Keycloak identity only.

This is the SINGLE authoritative entry point for binding an operator decision
(approve / deny / promote) to a verified Keycloak identity. It wraps the tested
`hg_operator_auth` validator so no gateway route re-implements token handling.

Security rules enforced here (KLR tranche, closing the OAK-011 gap):
- ID/access tokens are verified with RS256 against the LIVE Keycloak JWKS
  (fetched once and cached; `HG_OIDC_JWKS_FILE` supplies a fixture for tests).
  `verify_signature: False` is NEVER used on this path.
- Issuer, expiry, and role claims are checked; missing/invalid/expired/wrong-issuer
  → fail closed.
- The `service` role can never act as a human approver.
- Raw tokens never leave this module: callers receive an `OperatorIdentity`
  (hashed session id, no token material).
- `HG_OPERATOR_AUTH_MODE=keycloak` (default) requires a verified token;
  `demo_local` issues a demo-local identity that can never claim production auth.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Optional

from hg_operator_auth.identity import OperatorIdentity, validate_operator_identity
from hg_operator_auth.keycloak import (
    KeycloakTokenValidator, TokenValidationError, identity_from_token,
)
from hg_operator_auth.receipts import demo_local_identity
from hg_operator_auth.roles import can_approve_as_human, map_roles

_JWKS_CACHE: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_LOCK = threading.Lock()
_JWKS_TTL_S = 3600.0


class OperatorAuthError(Exception):
    """Fail-closed auth error → HTTP 401/403 at the route layer."""

    def __init__(self, code: str, status: int = 401) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def _issuer() -> str:
    base = (os.environ.get("KEYCLOAK_PUBLIC_URL")
            or os.environ.get("KEYCLOAK_URL", "http://localhost:8180")).rstrip("/")
    realm = os.environ.get("KEYCLOAK_REALM", "hg")
    return f"{base}/realms/{realm}"


def _internal_issuer() -> str:
    base = (os.environ.get("KEYCLOAK_INTERNAL_URL")
            or os.environ.get("KEYCLOAK_URL", "http://localhost:8180")).rstrip("/")
    realm = os.environ.get("KEYCLOAK_REALM", "hg")
    return f"{base}/realms/{realm}"


def auth_mode() -> str:
    return os.environ.get("HG_OPERATOR_AUTH_MODE", "keycloak").strip().lower()


def _load_jwks(*, force: bool = False) -> dict[str, Any]:
    """Return {kid: public_key}. Fixture file wins for tests; else live fetch."""
    fixture = os.environ.get("HG_OIDC_JWKS_FILE")
    if fixture:
        import jwt as pyjwt
        data = json.loads((open(fixture, encoding="utf-8")).read())
        return {k["kid"]: pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(k))
                for k in data["keys"] if k.get("alg") == "RS256"}
    with _JWKS_LOCK:
        fresh = (_JWKS_CACHE["keys"] is not None
                 and (time.time() - _JWKS_CACHE["fetched_at"]) < _JWKS_TTL_S)
        if fresh and not force:
            return _JWKS_CACHE["keys"]
        import httpx
        import jwt as pyjwt
        url = f"{_internal_issuer()}/protocol/openid-connect/certs"
        with httpx.Client(timeout=10.0) as client:
            data = client.get(url).json()
        keys = {k["kid"]: pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(k))
                for k in data["keys"] if k.get("alg") == "RS256"}
        _JWKS_CACHE.update(keys=keys, fetched_at=time.time())
        return keys


def build_validator() -> KeycloakTokenValidator:
    client_id = os.environ.get("KEYCLOAK_CLIENT_ID", "gateway-ui")
    source = "fixture_jwks" if os.environ.get("HG_OIDC_JWKS_FILE") \
        else "live_local_keycloak"
    return KeycloakTokenValidator(
        issuer=_issuer(), jwks=_load_jwks(), client_id=client_id,
        jwks_source=source)


def verify_operator_token(token: Optional[str], *, required_role: str = "hg.operator",
                          step_up_required: bool = False) -> OperatorIdentity:
    """Verify a bearer token → OperatorIdentity. Fail closed. No raw token retained."""
    if auth_mode() == "demo_local":
        # Demo-local: honest, validator-enforced non-production identity. A fresh
        # local identity carries a current auth_time so medium-risk recency holds;
        # production_operator_auth stays False (validator-enforced).
        import dataclasses
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        identity = dataclasses.replace(
            demo_local_identity(operator_id=os.environ.get(
                "HG_DEMO_OPERATOR_ID", "demo-operator-local")),
            auth_time=now)
        validate_operator_identity(identity)
        return identity
    if not token:
        raise OperatorAuthError("AUTH_MISSING_TOKEN", 401)
    try:
        validated = build_validator().validate(token, required_role=required_role)
    except TokenValidationError as exc:
        status = 403 if exc.code in ("AUTH_MISSING_ROLE", "AUTH_WRONG_AUDIENCE") else 401
        raise OperatorAuthError(exc.code, status) from exc
    if not can_approve_as_human(validated.roles):
        raise OperatorAuthError("AUTH_NOT_HUMAN_APPROVER", 403)
    identity = identity_from_token(validated, step_up_required=step_up_required)
    validate_operator_identity(identity)
    return identity


def bearer_from_headers(headers: Any) -> Optional[str]:
    auth = None
    try:
        auth = headers.get("authorization") or headers.get("Authorization")
    except Exception:
        return None
    if not auth or not auth.lower().startswith("bearer "):
        return None
    return auth.split(None, 1)[1].strip()


def identity_from_session(session: dict[str, Any], *,
                          required_role: str = "hg.operator") -> OperatorIdentity:
    """Derive an OperatorIdentity from a VERIFIED gateway browser session.

    The OIDC callback signature-verifies the id_token before minting the session
    (KLR hardening), so the session's `idp_sub` + roles are trustworthy. The
    browser holds only the opaque session cookie — no raw token is involved, so
    this path never sees token material. A session carries no amr/acr, so the
    identity has NO step-up evidence: high/restricted actions correctly fail
    closed (held) for a plain cookie session.
    """
    import hashlib
    from datetime import datetime, timezone
    subject = str(session.get("idp_sub") or "").strip()
    if not subject:
        raise OperatorAuthError("AUTH_MISSING_SUBJECT", 401)
    roles = tuple(map_roles(session.get("roles", [])) or ())
    # keep any explicit hg.* roles the session already carries
    raw_roles = tuple(session.get("roles", []))
    roles = tuple(dict.fromkeys(roles + tuple(r for r in raw_roles if r.startswith("hg."))))
    if not can_approve_as_human(raw_roles) and not can_approve_as_human(roles):
        raise OperatorAuthError("AUTH_NOT_HUMAN_APPROVER", 403)
    sid = str(session.get("session_id") or "")
    session_hash = ("sha256:" + hashlib.sha256(sid.encode("utf-8")).hexdigest()) if sid else ""
    created = session.get("created_at")
    identity = OperatorIdentity(
        provider="keycloak", issuer=_issuer(), subject=subject,
        display_name=str(session.get("principal_id") or ""), email="",
        roles=roles, session_id_hash=session_hash,
        auth_time=created, assurance_level="password",
        step_up_required=False, step_up_satisfied=False,
        production_operator_auth=True, demo_local_signing=False,
        step_up_evidence=())
    validate_operator_identity(identity)
    return identity


def verify_operator_request(request: Any, *, required_role: str = "hg.operator",
                            step_up_required: bool = False) -> OperatorIdentity:
    """Accept a Bearer token OR a verified gateway cookie session. Fail closed.

    Bearer is for API clients (and carries amr for step-up); the cookie session
    is for the logged-in browser panel. Bearer wins when present.
    """
    if auth_mode() == "demo_local":
        return verify_operator_token(None, required_role=required_role,
                                     step_up_required=step_up_required)
    token = bearer_from_headers(request.headers)
    if token:
        return verify_operator_token(token, required_role=required_role,
                                     step_up_required=step_up_required)
    # Cookie session fallback (browser panel).
    try:
        from hg_gateway.auth_routes import SESSION_COOKIE_NAME
        from hg_gateway.session_store import get_session
        sid = request.cookies.get(SESSION_COOKIE_NAME)
    except Exception:
        sid = None
    if not sid:
        raise OperatorAuthError("AUTH_MISSING_TOKEN", 401)
    session = get_session(sid)
    if not session:
        raise OperatorAuthError("AUTH_INVALID_SESSION", 401)
    return identity_from_session(session, required_role=required_role)


__all__ = [
    "OperatorAuthError", "auth_mode", "build_validator", "bearer_from_headers",
    "identity_from_session", "verify_operator_request", "verify_operator_token",
]
