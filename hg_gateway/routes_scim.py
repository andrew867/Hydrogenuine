"""
Pack 16: SCIM 2.0 — /scim/v2/Users, /scim/v2/Groups; group->role mapping per tenant.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from hg_gateway.auth import verify_api_key, get_tenant_context, require_tenant_admin
from hg_gateway.db import get_connection
from hg_core.tenancy.context import TenantContext

router = APIRouter(prefix="/scim/v2", tags=["scim"], dependencies=[Depends(verify_api_key)])


def _scim_user_from_row(row: Any) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "userName": row["user_name"],
        "displayName": row["display_name"] or row["user_name"],
        "active": bool(row["active"]),
        "meta": json.loads(row["meta_json"]) if row["meta_json"] else {},
        "externalId": row["external_id"],
    }


def _scim_group_from_row(row: Any) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "displayName": row["display_name"],
        "meta": json.loads(row["meta_json"]) if row["meta_json"] else {},
    }


@router.get("/Users")
def scim_list_users(
    tenant: TenantContext = Depends(get_tenant_context),
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=0, le=100),
):
    """List users (SCIM 2.0)."""
    tenant_id = tenant.tenant_id
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM scim_users WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()["n"]
        rows = conn.execute(
            """SELECT id, tenant_id, external_id, user_name, display_name, active, meta_json, created_at, updated_at
               FROM scim_users WHERE tenant_id = ? ORDER BY user_name LIMIT ? OFFSET ?""",
            (tenant_id, count, startIndex - 1),
        ).fetchall()
    resources = [_scim_user_from_row(r) for r in rows]
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": total,
        "startIndex": startIndex,
        "itemsPerPage": len(resources),
        "Resources": resources,
    }


@router.post("/Users")
def scim_create_user(
    body: Dict[str, Any],
    tenant: TenantContext = Depends(get_tenant_context),
    _: None = Depends(require_tenant_admin),
):
    """Create user (SCIM 2.0)."""
    tenant_id = tenant.tenant_id
    user_name = (body.get("userName") or "").strip()
    if not user_name:
        raise HTTPException(status_code=400, detail="userName required")
    display_name = (body.get("displayName") or user_name).strip()
    active = body.get("active", True)
    external_id = body.get("externalId")
    uid = str(uuid.uuid4())
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z")
    meta = body.get("meta") or {}
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO scim_users (id, tenant_id, external_id, user_name, display_name, active, meta_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (uid, tenant_id, external_id, user_name, display_name, 1 if active else 0, json.dumps(meta), now, now),
        )
    return {"id": uid, "userName": user_name, "displayName": display_name, "active": active, "meta": meta}


@router.get("/Users/{id}")
def scim_get_user(id: str, tenant: TenantContext = Depends(get_tenant_context)):
    """Get user by id."""
    tenant_id = tenant.tenant_id
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, tenant_id, external_id, user_name, display_name, active, meta_json FROM scim_users WHERE id = ? AND tenant_id = ?",
            (id, tenant_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return _scim_user_from_row(row)


@router.get("/Groups")
def scim_list_groups(
    tenant: TenantContext = Depends(get_tenant_context),
    startIndex: int = Query(1, ge=1),
    count: int = Query(100, ge=0, le=100),
):
    """List groups (SCIM 2.0)."""
    tenant_id = tenant.tenant_id
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM scim_groups WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()["n"]
        rows = conn.execute(
            """SELECT id, tenant_id, display_name, meta_json FROM scim_groups WHERE tenant_id = ? ORDER BY display_name LIMIT ? OFFSET ?""",
            (tenant_id, count, startIndex - 1),
        ).fetchall()
    resources = [_scim_group_from_row(r) for r in rows]
    return {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": total,
        "startIndex": startIndex,
        "itemsPerPage": len(resources),
        "Resources": resources,
    }


@router.post("/Groups")
def scim_create_group(
    body: Dict[str, Any],
    tenant: TenantContext = Depends(get_tenant_context),
    _: None = Depends(require_tenant_admin),
):
    """Create group (SCIM 2.0)."""
    tenant_id = tenant.tenant_id
    display_name = (body.get("displayName") or "").strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="displayName required")
    gid = str(uuid.uuid4())
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z")
    meta = body.get("meta") or {}
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO scim_groups (id, tenant_id, display_name, meta_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (gid, tenant_id, display_name, json.dumps(meta), now, now),
        )
    return {"id": gid, "displayName": display_name, "meta": meta}


@router.get("/Groups/{id}")
def scim_get_group(id: str, tenant: TenantContext = Depends(get_tenant_context)):
    """Get group by id."""
    tenant_id = tenant.tenant_id
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, tenant_id, display_name, meta_json FROM scim_groups WHERE id = ? AND tenant_id = ?",
            (id, tenant_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Group not found")
    return _scim_group_from_row(row)


@router.patch("/Groups/{id}")
def scim_patch_group(
    id: str,
    body: Dict[str, Any],
    tenant: TenantContext = Depends(get_tenant_context),
    _: None = Depends(require_tenant_admin),
):
    """Patch group (e.g. add members or role mapping)."""
    tenant_id = tenant.tenant_id
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM scim_groups WHERE id = ? AND tenant_id = ?", (id, tenant_id)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Group not found")
        ops = body.get("Operations") or []
        for op in ops:
            path = (op.get("path") or "").strip()
            value = op.get("value")
            if path == "roles" and isinstance(value, list):
                for role in value:
                    if isinstance(role, str) and role.strip():
                        conn.execute(
                            "INSERT OR IGNORE INTO scim_group_role_mapping (tenant_id, group_id, role) VALUES (?, ?, ?)",
                            (tenant_id, id, role.strip()),
                        )
    return scim_get_group(id)
