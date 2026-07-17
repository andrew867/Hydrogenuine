"""
Domain value segmentation (Pack 4): value profiles per domain/tenant/env.
VALUE_PROFILE_PUBLISHED, VALUE_PROFILE_APPLIED, VALUE_PROFILE_RESOLVED.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def publish_value_profile(
    *,
    domain_id: str,
    weights: List[Dict[str, Any]],
    constraints: List[Dict[str, Any]],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    tenant_id: Optional[str] = None,
    environment: Optional[str] = None,
    version: Optional[str] = None,
    notes: str = "",
) -> str:
    """
    Write value profile artifact and emit VALUE_PROFILE_PUBLISHED.
    weights: [{dimension, weight}]. constraints: [{dimension, op, value}].
    Returns profile_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    profile_id = "vp_" + hashlib.sha256(
        f"{domain_id}:{tenant_id or ''}:{environment or ''}:{ts}".encode()
    ).hexdigest()[:16]
    ver = version or "1"
    root = workspace_root / "artifacts" / "values" / "profiles"
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{profile_id}.json"
    profile = {
        "profile_id": profile_id,
        "version": ver,
        "domain_id": domain_id,
        "tenant_id": tenant_id or "",
        "environment": environment or "",
        "weights": weights,
        "constraints": constraints,
        "notes": notes,
        "published_ts": ts,
    }
    artifact_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    emit(
        "VALUE_PROFILE_PUBLISHED",
        "value_profile",
        profile_id,
        {
            "profile_id": profile_id,
            "version": ver,
            "domain_id": domain_id,
            "artifact_id": str(artifact_path),
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return profile_id


def resolve_profile(
    workspace_root: Path,
    domain_id: str,
    tenant_id: Optional[str] = None,
    environment: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Pick the active value profile by domain, tenant, environment.
    Returns the most recently published profile matching scope (tenant/env optional).
    """
    workspace_root = Path(workspace_root)
    root = workspace_root / "artifacts" / "values" / "profiles"
    if not root.exists():
        return None
    candidates: List[tuple[float, Dict[str, Any]]] = []
    for p in root.glob("vp_*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if data.get("domain_id") != domain_id:
                continue
            if tenant_id is not None and data.get("tenant_id") and data.get("tenant_id") != tenant_id:
                continue
            if environment is not None and data.get("environment") and data.get("environment") != environment:
                continue
            ts = data.get("published_ts") or "0"
            candidates.append((ts, data))
        except (json.JSONDecodeError, OSError):
            continue
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def record_value_profile_applied(
    *,
    profile_id: str,
    decision_id: Optional[str] = None,
    work_item_id: Optional[str] = None,
    action_id: Optional[str] = None,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    reason: str = "",
) -> str:
    """Emit VALUE_PROFILE_APPLIED (which profile governed a decision/work item). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {"profile_id": profile_id, "ts": ts, "reason": reason}
    if decision_id:
        payload["decision_id"] = decision_id
    if work_item_id:
        payload["work_item_id"] = work_item_id
    if action_id:
        payload["action_id"] = action_id
    return emit(
        "VALUE_PROFILE_APPLIED",
        "value_profile",
        profile_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def publish_value_profile_resolution(
    *,
    conflict_id: str,
    resolution: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Write resolution artifact and emit VALUE_PROFILE_RESOLVED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    res_id = "vpr_" + hashlib.sha256(f"{conflict_id}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "values" / "resolutions"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{res_id}.json"
    path.write_text(json.dumps({"resolution_id": res_id, "conflict_id": conflict_id, "resolution": resolution, "ts": ts}, indent=2), encoding="utf-8")
    return emit(
        "VALUE_PROFILE_RESOLVED",
        "value_profile",
        res_id,
        {"resolution_id": res_id, "conflict_id": conflict_id, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
