"""
Principals and availability (Pack2-08). Real persistence in gateway SQLite.
Types: user (human operator), agent (entity/agent), service_account.
Availability: timezone, on_call_hours (JSON), status (online|offline|away), escalation_chain (JSON list of principal ids).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from hg_gateway.db import get_connection, _get_db_path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def list_principals(
    tenant_id: str,
    include_disabled: bool = False,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List principals for the given tenant. By default excludes disabled. Returns list of principal dicts with id, type, label, timezone, on_call_hours, status, escalation_chain, disabled, created_at, updated_at."""
    with get_connection(db_path) as conn:
        if include_disabled:
            rows = conn.execute(
                "SELECT id, type, label, timezone, on_call_hours, status, escalation_chain, disabled, created_at, updated_at FROM principals WHERE tenant_id = ? ORDER BY id",
                (tenant_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, type, label, timezone, on_call_hours, status, escalation_chain, disabled, created_at, updated_at FROM principals WHERE tenant_id = ? AND (disabled IS NULL OR disabled = 0) ORDER BY id",
                (tenant_id,),
            ).fetchall()
        out = []
        for r in rows:
            out.append(_row_to_principal(r))
        return out


def get_principal(principal_id: str, tenant_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get one principal by id for the given tenant. Returns None if not found or belongs to another tenant. Includes disabled flag."""
    with get_connection(db_path) as conn:
        r = conn.execute(
            "SELECT id, type, label, timezone, on_call_hours, status, escalation_chain, disabled, created_at, updated_at FROM principals WHERE id = ? AND tenant_id = ?",
            (principal_id, tenant_id),
        ).fetchone()
        if not r:
            return None
        return _row_to_principal(r)


def _row_to_principal(r: Any) -> Dict[str, Any]:
    on_call = r["on_call_hours"]
    chain = r["escalation_chain"]
    # sqlite3.Row supports keys() and []; no .get()
    disabled = 0
    if "disabled" in r.keys() and r["disabled"] is not None:
        disabled = r["disabled"]
    return {
        "id": r["id"],
        "type": r["type"],
        "label": r["label"],
        "timezone": r["timezone"],
        "on_call_hours": json.loads(on_call) if on_call else None,
        "status": r["status"] or "offline",
        "escalation_chain": json.loads(chain) if chain else None,
        "disabled": bool(disabled),
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }


def upsert_principal(
    principal_id: str,
    type: str,
    label: str,
    *,
    tenant_id: str = "default",
    timezone: Optional[str] = None,
    on_call_hours: Optional[Dict[str, Any]] = None,
    status: str = "offline",
    escalation_chain: Optional[List[str]] = None,
    db_path: Optional[str] = None,
) -> None:
    """Create or replace principal for the given tenant. type: user | agent | service_account; status: online | offline | away."""
    now = _now()
    on_call_json = json.dumps(on_call_hours) if on_call_hours is not None else None
    chain_json = json.dumps(escalation_chain) if escalation_chain is not None else None
    if type not in ("user", "agent", "service_account"):
        type = "user"
    if status not in ("online", "offline", "away"):
        status = "offline"
    with get_connection(db_path) as conn:
        existing = get_principal(principal_id, tenant_id, db_path)
        if existing:
            conn.execute(
                """UPDATE principals SET type=?, label=?, timezone=?, on_call_hours=?, status=?, escalation_chain=?, updated_at=?
                   WHERE id = ? AND tenant_id = ?""",
                (type, label, timezone, on_call_json, status, chain_json, now, principal_id, tenant_id),
            )
        else:
            # If id exists for another tenant, we get UNIQUE constraint - let it raise
            conn.execute(
                """INSERT INTO principals (id, tenant_id, type, label, timezone, on_call_hours, status, escalation_chain, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (principal_id, tenant_id, type, label, timezone, on_call_json, status, chain_json, now, now),
            )


def update_availability(
    principal_id: str,
    *,
    tenant_id: str = "default",
    timezone: Optional[str] = None,
    on_call_hours: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
    escalation_chain: Optional[List[str]] = None,
    disabled: Optional[bool] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Update availability and disabled fields for a principal. Returns True if principal existed for this tenant."""
    with get_connection(db_path) as conn:
        r = conn.execute(
            "SELECT id, timezone, on_call_hours, status, escalation_chain, disabled FROM principals WHERE id = ? AND tenant_id = ?",
            (principal_id, tenant_id),
        ).fetchone()
        if not r:
            return False
        now = _now()
        tz = timezone if timezone is not None else r["timezone"]
        on_call = json.dumps(on_call_hours) if on_call_hours is not None else r["on_call_hours"]
        st = status if status is not None else r["status"]
        if st and st not in ("online", "offline", "away"):
            st = r["status"]
        chain = json.dumps(escalation_chain) if escalation_chain is not None else r["escalation_chain"]
        disc = 1 if (disabled if disabled is not None else bool(r.get("disabled") or 0)) else 0
        conn.execute(
            "UPDATE principals SET timezone=?, on_call_hours=?, status=?, escalation_chain=?, disabled=?, updated_at=? WHERE id=? AND tenant_id=?",
            (tz, on_call, st, chain, disc, now, principal_id, tenant_id),
        )
        return True


def resolve_available_principal(chain_ids: List[str], tenant_id: str = "default", db_path: Optional[str] = None) -> Optional[str]:
    """Return the first principal id in chain_ids whose status is online (or away) and not disabled, scoped to tenant. Used for approval routing."""
    if not chain_ids:
        return None
    with get_connection(db_path) as conn:
        placeholders = ",".join("?" * len(chain_ids))
        rows = conn.execute(
            f"SELECT id, status, COALESCE(disabled, 0) AS disabled FROM principals WHERE id IN ({placeholders}) AND tenant_id = ? ORDER BY id",
            tuple(chain_ids) + (tenant_id,),
        ).fetchall()
    by_id = {r["id"]: (r["status"], r["disabled"]) for r in rows}
    for pid in chain_ids:
        st, disc = by_id.get(pid, ("offline", 1))
        if disc:
            continue
        if st in ("online", "away"):
            return pid
    return chain_ids[0] if chain_ids else None
