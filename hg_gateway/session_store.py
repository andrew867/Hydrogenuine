"""
Gateway browser session persistence helpers.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from hg_gateway.db import get_connection

SESSION_COOKIE_NAME = "hg_session"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def create_session(
    tenant_id: str,
    principal_id: str,
    roles: List[str],
    *,
    ttl_seconds: int,
    idp_sub: Optional[str] = None,
) -> tuple[str, str]:
    session_id = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(24)
    created_at = now_iso()
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat().replace("+00:00", "Z")
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO sessions (session_id, tenant_id, principal_id, roles_json, csrf_token, created_at, expires_at, idp_sub)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, tenant_id, principal_id, json.dumps(roles), csrf_token, created_at, expires_at, idp_sub),
        )
    return session_id, csrf_token


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT session_id, tenant_id, principal_id, roles_json, csrf_token, created_at, expires_at, idp_sub FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    if not row:
        return None
    expires_at = row["expires_at"]
    if expires_at and expires_at < now_iso():
        delete_session(session_id)
        return None
    return {
        "session_id": row["session_id"],
        "tenant_id": row["tenant_id"],
        "principal_id": row["principal_id"],
        "roles": json.loads(row["roles_json"]) if row["roles_json"] else [],
        "csrf_token": row["csrf_token"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "idp_sub": row["idp_sub"],
    }


def delete_session(session_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))


def list_sessions_for_principal(tenant_id: str, principal_id: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT session_id, tenant_id, principal_id, roles_json, created_at, expires_at
               FROM sessions WHERE tenant_id = ? AND principal_id = ? AND expires_at > ?""",
            (tenant_id, principal_id, now_iso()),
        ).fetchall()
    out: List[Dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "session_id": row["session_id"],
                "tenant_id": row["tenant_id"],
                "principal_id": row["principal_id"],
                "roles": json.loads(row["roles_json"]) if row["roles_json"] else [],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
            }
        )
    return out
