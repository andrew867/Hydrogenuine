"""
Step-up auth (Pack2-06): TOTP challenge/verify, JWT step-up tokens.
Real verification; secrets stored encrypted in gateway DB (stepup_secrets table).

To avoid re-enrolling after server restart: set HG_GATEWAY_DB_PATH to an absolute
path (e.g. workspace/memory/gateway.sqlite3) and keep HG_STEPUP_ENCRYPTION_KEY
(or HG_GATEWAY_API_KEY, from which the key is derived) unchanged across restarts.
"""

from __future__ import annotations

import base64
import hashlib
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from hg_gateway.db import get_connection

# TTL for step-up token (spec: 5 minutes)
STEPUP_TOKEN_TTL_SEC = 300
# Challenge expiry (2 minutes to enter code)
CHALLENGE_TTL_SEC = 120


def _fernet_key() -> bytes:
    """Fernet key: HG_STEPUP_ENCRYPTION_KEY (base64 string) or derived from HG_GATEWAY_API_KEY. Must be 44-byte url-safe base64."""
    raw = os.environ.get("HG_STEPUP_ENCRYPTION_KEY", "").strip()
    if raw:
        return raw.encode() if isinstance(raw, str) else raw
    return base64.urlsafe_b64encode(hashlib.sha256(os.environ.get("HG_GATEWAY_API_KEY", "stepup-default-secret").encode()).digest())


def _fernet():
    from cryptography.fernet import Fernet
    key = _fernet_key()
    if len(key) != 32:
        key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
    return Fernet(key)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _jwt_secret() -> str:
    return os.environ.get("HG_STEPUP_JWT_SECRET", "").strip() or os.environ.get("HG_GATEWAY_API_KEY", "stepup-jwt-secret")


def enroll(user_id: str, secret: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Enroll TOTP for user_id. If secret is None, generate one. Store encrypted. Return { secret, provisioning_uri }."""
    import pyotp
    if not secret:
        secret = pyotp.random_base32()
    now = _now()
    f = _fernet()
    encrypted = f.encrypt(secret.encode()).decode()
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO stepup_secrets (user_id, encrypted_secret, created_at) VALUES (?, ?, ?)",
            (user_id, encrypted, now),
        )
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user_id, issuer_name="HG")
    return {"secret": secret, "provisioning_uri": provisioning_uri}


def is_enrolled(user_id: str, db_path: Optional[str] = None) -> bool:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT 1 FROM stepup_secrets WHERE user_id = ?", (user_id,)).fetchone()
    return bool(row)


def create_challenge(user_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Create a step-up challenge for user_id. Returns { challenge_id, method } or None if user not enrolled."""
    with get_connection(db_path) as conn:
        r = conn.execute("SELECT 1 FROM stepup_secrets WHERE user_id = ?", (user_id,)).fetchone()
        if not r:
            return None
        challenge_id = str(uuid.uuid4())
        expires = (datetime.now(timezone.utc) + timedelta(seconds=CHALLENGE_TTL_SEC)).isoformat().replace("+00:00", "Z")
        conn.execute(
            "INSERT INTO stepup_challenges (challenge_id, user_id, expires_at) VALUES (?, ?, ?)",
            (challenge_id, user_id, expires),
        )
    return {"challenge_id": challenge_id, "method": "totp"}


def verify_challenge(challenge_id: str, code: str, db_path: Optional[str] = None) -> Optional[str]:
    """Verify TOTP code for challenge; if valid, delete challenge and return step-up JWT. Else None."""
    import pyotp
    import jwt as pyjwt
    with get_connection(db_path) as conn:
        r = conn.execute(
            "SELECT user_id, expires_at FROM stepup_challenges WHERE challenge_id = ?",
            (challenge_id,),
        ).fetchone()
        if not r:
            return None
        user_id, expires_at = r["user_id"], r["expires_at"]
        if expires_at < _now():
            conn.execute("DELETE FROM stepup_challenges WHERE challenge_id = ?", (challenge_id,))
            return None
        secret_row = conn.execute("SELECT encrypted_secret FROM stepup_secrets WHERE user_id = ?", (user_id,)).fetchone()
        if not secret_row:
            return None
        f = _fernet()
        try:
            secret = f.decrypt(secret_row["encrypted_secret"].encode()).decode()
        except Exception:
            return None
        if not pyotp.TOTP(secret).verify(code, valid_window=1):
            return None
        conn.execute("DELETE FROM stepup_challenges WHERE challenge_id = ?", (challenge_id,))
    # Mint JWT: sub=user_id, action_class=*, exp=5min
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "action_class": "*",
        "iat": now,
        "exp": now + timedelta(seconds=STEPUP_TOKEN_TTL_SEC),
    }
    tok = pyjwt.encode(payload, _jwt_secret(), algorithm="HS256")
    return tok if isinstance(tok, str) else tok.decode()


def verify_stepup_token(token: str, action_class: str) -> Optional[Dict[str, Any]]:
    """Verify step-up JWT; require token to cover action_class (payload action_class '*' or match). Return payload or None."""
    import jwt as pyjwt
    try:
        payload = pyjwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except Exception:
        return None
    allowed = payload.get("action_class") == "*" or payload.get("action_class") == action_class
    if not allowed:
        return None
    return payload


def requires_stepup_for_approval(approval: Dict[str, Any]) -> bool:
    """True if this approval is high-risk and requires step-up."""
    risk = (approval.get("risk") or "").strip().lower()
    return risk == "high"


def record_stepup_audit(
    tenant_id: str,
    user_id: str,
    action_class: str,
    approval_id: Optional[str] = None,
    outcome: str = "used",
    db_path: Optional[str] = None,
) -> None:
    """Append an audit record when step-up is required or token is used (compliance/debugging)."""
    import json
    payload = {
        "user_id": user_id,
        "action_class": action_class,
        "approval_id": approval_id,
        "outcome": outcome,
        "ts": _now(),
    }
    try:
        with get_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO audit_events (tenant_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
                (tenant_id, "stepup_audit", json.dumps(payload), _now()),
            )
    except Exception:
        pass


def cleanup_expired_challenges(db_path: Optional[str] = None) -> int:
    """Delete expired rows from stepup_challenges. Returns count deleted. Run periodically or on next create_challenge."""
    with get_connection(db_path) as conn:
        cur = conn.execute("DELETE FROM stepup_challenges WHERE expires_at < ?", (_now(),))
        return cur.rowcount
