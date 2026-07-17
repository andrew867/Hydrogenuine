"""
Pack 15.3: Steering profiles store — CRUD, per-tenant defaults, per-chat override, resolution.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from hg_gateway.db import get_connection

STEERING_TYPES = ("legal", "privacy", "brand", "emotion", "safety", "custom")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def steering_profile_create(
    *,
    profile_id: str,
    tenant_id: Optional[str] = None,
    type: str,
    strength: float = 0.5,
    target: Optional[Dict[str, Any]] = None,
    prompt_fragments: Optional[List[str]] = None,
    classifier_thresholds: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a steering profile. tenant_id None = global default."""
    if type not in STEERING_TYPES:
        type = "custom"
    now = _now()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO steering_profiles (
            profile_id, tenant_id, type, strength, target_json, prompt_fragments_json,
            classifier_thresholds_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                profile_id,
                tenant_id,
                type,
                max(0.0, min(1.0, strength)),
                json.dumps(target) if target else None,
                json.dumps(prompt_fragments) if prompt_fragments else None,
                json.dumps(classifier_thresholds) if classifier_thresholds else None,
                now,
            ),
        )
    return steering_profile_get(profile_id) or {}


def steering_profile_get(profile_id: str) -> Optional[Dict[str, Any]]:
    """Get a steering profile by id."""
    with get_connection() as conn:
        r = conn.execute(
            """SELECT profile_id, tenant_id, type, strength, target_json, prompt_fragments_json,
               classifier_thresholds_json, updated_at FROM steering_profiles WHERE profile_id = ?""",
            (profile_id,),
        ).fetchone()
        if not r:
            return None
        return _row_to_profile(r)


def steering_profile_list(
    tenant_id: Optional[str] = None,
    include_global: bool = True,
) -> List[Dict[str, Any]]:
    """List steering profiles: for tenant_id (tenant + global if include_global), or all if tenant_id None."""
    with get_connection() as conn:
        if tenant_id:
            if include_global:
                rows = conn.execute(
                    """SELECT profile_id, tenant_id, type, strength, target_json, prompt_fragments_json,
                       classifier_thresholds_json, updated_at FROM steering_profiles
                       WHERE tenant_id = ? OR tenant_id IS NULL ORDER BY (tenant_id IS NULL), tenant_id, profile_id""",
                    (tenant_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT profile_id, tenant_id, type, strength, target_json, prompt_fragments_json,
                       classifier_thresholds_json, updated_at FROM steering_profiles
                       WHERE tenant_id = ? ORDER BY profile_id""",
                    (tenant_id,),
                ).fetchall()
        else:
            rows = conn.execute(
                """SELECT profile_id, tenant_id, type, strength, target_json, prompt_fragments_json,
                   classifier_thresholds_json, updated_at FROM steering_profiles ORDER BY (tenant_id IS NULL), tenant_id, profile_id"""
            ).fetchall()
        return [_row_to_profile(r) for r in rows]


def steering_profile_update(
    profile_id: str,
    *,
    strength: Optional[float] = None,
    target: Optional[Dict[str, Any]] = None,
    prompt_fragments: Optional[List[str]] = None,
    classifier_thresholds: Optional[Dict[str, Any]] = None,
) -> bool:
    """Update a steering profile. Returns True if found and updated."""
    now = _now()
    with get_connection() as conn:
        cur = conn.execute(
            """UPDATE steering_profiles SET
            strength = COALESCE(?, strength), target_json = COALESCE(?, target_json),
            prompt_fragments_json = COALESCE(?, prompt_fragments_json),
            classifier_thresholds_json = COALESCE(?, classifier_thresholds_json),
            updated_at = ? WHERE profile_id = ?""",
            (
                strength if strength is not None else None,
                json.dumps(target) if target is not None else None,
                json.dumps(prompt_fragments) if prompt_fragments is not None else None,
                json.dumps(classifier_thresholds) if classifier_thresholds is not None else None,
                now,
                profile_id,
            ),
        )
        return cur.rowcount > 0


def steering_profile_delete(profile_id: str) -> bool:
    """Delete a steering profile and remove from tenant defaults. Returns True if deleted."""
    with get_connection() as conn:
        conn.execute("DELETE FROM tenant_default_steering WHERE profile_id = ?", (profile_id,))
        cur = conn.execute("DELETE FROM steering_profiles WHERE profile_id = ?", (profile_id,))
        return cur.rowcount > 0


def _row_to_profile(r: Any) -> Dict[str, Any]:
    return {
        "profile_id": r["profile_id"],
        "tenant_id": r["tenant_id"],
        "type": r["type"],
        "strength": float(r["strength"]),
        "target": json.loads(r["target_json"]) if r["target_json"] else None,
        "prompt_fragments": json.loads(r["prompt_fragments_json"]) if r["prompt_fragments_json"] else None,
        "classifier_thresholds": json.loads(r["classifier_thresholds_json"]) if r["classifier_thresholds_json"] else None,
        "updated_at": r["updated_at"],
    }


def get_tenant_default_profile_ids(tenant_id: str) -> List[str]:
    """Return ordered list of profile_ids that are the tenant's default set."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT profile_id FROM tenant_default_steering WHERE tenant_id = ? ORDER BY sort_order, profile_id",
            (tenant_id,),
        ).fetchall()
        return [r["profile_id"] for r in rows]


def set_tenant_default_profile_ids(tenant_id: str, profile_ids: List[str]) -> None:
    """Set the tenant's default steering profile set."""
    with get_connection() as conn:
        conn.execute("DELETE FROM tenant_default_steering WHERE tenant_id = ?", (tenant_id,))
        for i, pid in enumerate(profile_ids):
            conn.execute(
                "INSERT INTO tenant_default_steering (tenant_id, profile_id, sort_order) VALUES (?, ?, ?)",
                (tenant_id, pid, i),
            )


def get_chat_steering_profile_ids(tenant_id: str, chat_id: str) -> Optional[List[str]]:
    """Return per-chat override profile_ids, or None if not set. Reads from chats.steering_profile_ids."""
    with get_connection() as conn:
        r = conn.execute(
            "SELECT steering_profile_ids FROM chats WHERE tenant_id = ? AND chat_id = ?",
            (tenant_id, chat_id),
        ).fetchone()
        if not r or not r["steering_profile_ids"]:
            return None
        try:
            return json.loads(r["steering_profile_ids"])
        except (json.JSONDecodeError, TypeError):
            return None


def set_chat_steering_profile_ids(tenant_id: str, chat_id: str, profile_ids: Optional[List[str]]) -> None:
    """Set per-chat steering override. profile_ids None clears override."""
    with get_connection() as conn:
        val = json.dumps(profile_ids) if profile_ids else None
        conn.execute(
            "UPDATE chats SET steering_profile_ids = ? WHERE tenant_id = ? AND chat_id = ?",
            (val, tenant_id, chat_id),
        )


def resolve_steering_profiles(
    tenant_id: str,
    chat_id: Optional[str] = None,
    run_override: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Resolve active steering profiles: run_override > per-chat override > tenant defaults.
    Returns list of profile dicts (with prompt_fragments, classifier_thresholds) in order.
    """
    if run_override is not None:
        profile_ids = run_override
    elif chat_id:
        profile_ids = get_chat_steering_profile_ids(tenant_id, chat_id)
        if profile_ids is None:
            profile_ids = get_tenant_default_profile_ids(tenant_id)
    else:
        profile_ids = get_tenant_default_profile_ids(tenant_id)
    if not profile_ids:
        return []
    out = []
    for pid in profile_ids:
        p = steering_profile_get(pid)
        if p and (p.get("tenant_id") is None or p.get("tenant_id") == tenant_id):
            out.append(p)
    return out
