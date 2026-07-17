"""
Pack 17: Per-tenant retention policy (chats_days, docs_days, proofs_days, logs_days, legal_hold).
Stored in gateway DB tenant_retention table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from hg_gateway.db import get_connection


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_retention_policy(tenant_id: str) -> Dict[str, Any]:
    """Return retention policy for tenant. Inserts default row if missing."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT tenant_id, chats_days, docs_days, proofs_days, logs_days, legal_hold_enabled, updated_at FROM tenant_retention WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchone()
        if row:
            return {
                "tenant_id": row["tenant_id"],
                "chats_days": row["chats_days"],
                "docs_days": row["docs_days"],
                "proofs_days": row["proofs_days"],
                "logs_days": row["logs_days"],
                "legal_hold_enabled": bool(row["legal_hold_enabled"]),
                "updated_at": row["updated_at"],
            }
        # Insert default
        now = _now_iso()
        conn.execute(
            """INSERT INTO tenant_retention (tenant_id, chats_days, docs_days, proofs_days, logs_days, legal_hold_enabled, updated_at)
               VALUES (?, 90, 90, 30, 30, 0, ?)""",
            (tenant_id, now),
        )
    return {
        "tenant_id": tenant_id,
        "chats_days": 90,
        "docs_days": 90,
        "proofs_days": 30,
        "logs_days": 30,
        "legal_hold_enabled": False,
        "updated_at": now,
    }


def set_retention_policy(
    tenant_id: str,
    chats_days: int | None = None,
    docs_days: int | None = None,
    proofs_days: int | None = None,
    logs_days: int | None = None,
    legal_hold_enabled: bool | None = None,
) -> Dict[str, Any]:
    """Update retention policy; partial update. Returns current policy."""
    now = _now_iso()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT chats_days, docs_days, proofs_days, logs_days, legal_hold_enabled FROM tenant_retention WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchone()
        if row:
            c, d, p, log_d, hold = row["chats_days"], row["docs_days"], row["proofs_days"], row["logs_days"], bool(row["legal_hold_enabled"])
        else:
            c, d, p, log_d, hold = 90, 90, 30, 30, False
        if chats_days is not None:
            c = max(1, int(chats_days))
        if docs_days is not None:
            d = max(1, int(docs_days))
        if proofs_days is not None:
            p = max(1, int(proofs_days))
        if logs_days is not None:
            log_d = max(1, int(logs_days))
        if legal_hold_enabled is not None:
            hold = bool(legal_hold_enabled)
        conn.execute(
            """INSERT INTO tenant_retention (tenant_id, chats_days, docs_days, proofs_days, logs_days, legal_hold_enabled, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(tenant_id) DO UPDATE SET
                 chats_days=excluded.chats_days, docs_days=excluded.docs_days,
                 proofs_days=excluded.proofs_days, logs_days=excluded.logs_days,
                 legal_hold_enabled=excluded.legal_hold_enabled, updated_at=excluded.updated_at""",
            (tenant_id, c, d, p, log_d, 1 if hold else 0, now),
        )
    return get_retention_policy(tenant_id)


def legal_hold_enabled(tenant_id: str) -> bool:
    """True if tenant has legal hold (blocks purge/delete)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT legal_hold_enabled FROM tenant_retention WHERE tenant_id = ?",
            (tenant_id,),
        ).fetchone()
        return bool(row["legal_hold_enabled"]) if row else False
