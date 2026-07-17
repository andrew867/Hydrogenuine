"""
Conflict detection (Pack 4): value, policy, contract conflicts.
CONFLICT_DETECTED, CONFLICT_WORK_ITEM_CREATED, CONFLICT_RESOLUTION_PUBLISHED.
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


def _check_constraint(weight_val: float, op: str, constraint_val: float) -> bool:
    """Return True if weight satisfies constraint (dimension op value)."""
    if op == ">=":
        return weight_val >= constraint_val
    if op == "<=":
        return weight_val <= constraint_val
    if op == ">":
        return weight_val > constraint_val
    if op == "<":
        return weight_val < constraint_val
    if op == "==":
        return weight_val == constraint_val
    return False


def detect_value_conflict(
    decision_weights: List[Dict[str, Any]],
    profile: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Return conflict info if decision weights violate profile constraints; else None.
    decision_weights: [{dimension, weight}]. profile: from resolve_profile (has constraints).
    """
    constraints = profile.get("constraints") or []
    if not constraints:
        return None
    by_dim = {w.get("dimension"): w.get("weight") for w in (decision_weights or []) if w.get("dimension") is not None}
    violations: List[Dict[str, Any]] = []
    for c in constraints:
        dim = c.get("dimension")
        op = c.get("op")
        val = c.get("value")
        if dim is None or op is None or val is None:
            continue
        w = by_dim.get(dim)
        if w is None:
            continue
        if not _check_constraint(float(w), op, float(val)):
            violations.append({"dimension": dim, "op": op, "value": val, "actual": w})
    if not violations:
        return None
    return {"type": "value", "violations": violations, "profile_id": profile.get("profile_id")}


def emit_conflict_detected(
    *,
    conflict_type: str,
    scope: Dict[str, str],
    refs: List[Dict[str, Any]],
    scope_actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    rationale: Optional[str] = None,
) -> str:
    """
    Write rationale artifact and emit CONFLICT_DETECTED. conflict_type: value|policy|contract.
    Returns conflict_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    conflict_id = "conf_" + hashlib.sha256(f"{conflict_type}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "conflicts"
    root.mkdir(parents=True, exist_ok=True)
    rationale_path = root / f"{conflict_id}.json"
    rationale_path.write_text(
        json.dumps({"conflict_id": conflict_id, "conflict_type": conflict_type, "refs": refs, "rationale": rationale or "", "ts": ts}, indent=2),
        encoding="utf-8",
    )
    emit(
        "CONFLICT_DETECTED",
        "conflict",
        conflict_id,
        {
            "conflict_id": conflict_id,
            "conflict_type": conflict_type,
            "scope": scope,
            "ts": ts,
            "refs": refs,
            "rationale_artifact_id": str(rationale_path),
        },
        scope=scope,
        actor=scope_actor,
        workspace_root=workspace_root,
    )
    return conflict_id


def create_conflict_work_item(
    *,
    conflict_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    title: Optional[str] = None,
) -> tuple[str, str]:
    """
    Emit CONFLICT_WORK_ITEM_CREATED and create a work item for reviewer arbitration.
    Returns (event_id, work_item_id).
    """
    workspace_root = Path(workspace_root or ".")
    from hg_core.work_items import create_work_item
    wi_id = create_work_item(
        wi_type="task",
        title=title or f"Resolve conflict {conflict_id}",
        scope=scope,
        actor=actor,
        description=f"Conflict {conflict_id} requires reviewer arbitration.",
        priority="high",
        workspace_root=workspace_root,
    )
    ts = _iso_ts()
    ev_id = emit(
        "CONFLICT_WORK_ITEM_CREATED",
        "conflict",
        conflict_id,
        {"conflict_id": conflict_id, "work_item_id": wi_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return ev_id, wi_id


def publish_conflict_resolution(
    *,
    conflict_id: str,
    resolution: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Write resolution artifact and emit CONFLICT_RESOLUTION_PUBLISHED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    res_id = "cres_" + hashlib.sha256(f"{conflict_id}:{ts}".encode()).hexdigest()[:16]
    root = workspace_root / "artifacts" / "conflicts" / "resolutions"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{res_id}.json"
    path.write_text(
        json.dumps({"resolution_id": res_id, "conflict_id": conflict_id, "resolution": resolution, "ts": ts}, indent=2),
        encoding="utf-8",
    )
    return emit(
        "CONFLICT_RESOLUTION_PUBLISHED",
        "conflict",
        res_id,
        {"resolution_id": res_id, "conflict_id": conflict_id, "artifact_id": str(path), "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
