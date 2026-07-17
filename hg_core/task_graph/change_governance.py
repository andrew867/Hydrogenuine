"""
Change governance (G1–G5): proposal schema, static validation, shadow mode, rollback, audit trail.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROPOSALS_DIR = "memory/automation/dag_proposals"
LAST_KNOWN_GOOD_DIR = "memory/automation/last_known_good"
AUDIT_TRAIL_PATH = "memory/automation/change_audit.jsonl"

REQUIRED_PROPOSAL_FIELDS = ("proposal_id", "created_at", "originating_run_id", "scope", "risk_level")
ALLOWED_SCOPES = ("single_workflow", "shared_component")
ALLOWED_RISK_LEVELS = ("low", "medium", "high")
ALLOWED_NODE_TYPES = frozenset({"tool", "agent", "loop", "gate"})


def _proposals_path(workspace_root: Path) -> Path:
    return workspace_root / PROPOSALS_DIR


def _audit_path(workspace_root: Path) -> Path:
    return workspace_root / AUDIT_TRAIL_PATH


def _lkg_path(workspace_root: Path, scope: str) -> Path:
    safe = scope.replace("/", "_").replace("\\", "_")
    return workspace_root / LAST_KNOWN_GOOD_DIR / f"{safe}.json"


def validate_proposal_schema(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    G2 static validation: schema and allowed values.
    Returns (True, []) if valid; (False, list of error messages) if invalid.
    """
    errors: List[str] = []
    for field in REQUIRED_PROPOSAL_FIELDS:
        if field not in payload:
            errors.append(f"missing_field_{field}")
    if payload.get("scope") not in ALLOWED_SCOPES:
        errors.append("invalid_scope")
    if payload.get("risk_level") not in ALLOWED_RISK_LEVELS:
        errors.append("invalid_risk_level")
    if "validation_plan" not in payload and "rollback_plan" not in payload:
        errors.append("missing_validation_or_rollback_plan")
    return (len(errors) == 0, errors)


def validate_proposal_node_types(change_payload: Any) -> Tuple[bool, List[str]]:
    """
    G2: If proposal contains node list, ensure only allowed node types.
    change_payload may be a DAG dict with "nodes" list; each node has "type".
    """
    errors: List[str] = []
    if not isinstance(change_payload, dict):
        return True, []
    nodes = change_payload.get("nodes")
    if not isinstance(nodes, list):
        return True, []
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            continue
        t = n.get("type")
        if t and t not in ALLOWED_NODE_TYPES:
            errors.append(f"node_{i}_invalid_type_{t}")
    return (len(errors) == 0, errors)


def save_proposal(
    workspace_root: Path,
    payload: Dict[str, Any],
) -> Path:
    """Save proposal to PROPOSALS_DIR; ensure proposal_id and created_at if missing."""
    root = Path(workspace_root)
    payload = dict(payload)
    if "proposal_id" not in payload:
        payload["proposal_id"] = f"prop_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    if "created_at" not in payload:
        payload["created_at"] = datetime.now(timezone.utc).isoformat()
    path = _proposals_path(root) / f"{payload['proposal_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def load_proposal(workspace_root: Path, proposal_id: str) -> Optional[Dict[str, Any]]:
    """Load proposal by id."""
    path = _proposals_path(workspace_root) / f"{proposal_id}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_last_known_good(workspace_root: Path, scope: str, config: Dict[str, Any]) -> Path:
    """G4: Save last known good configuration for scope before applying change."""
    path = _lkg_path(workspace_root, scope)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"scope": scope, "saved_at": datetime.now(timezone.utc).isoformat(), "config": config}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def rollback_scope(workspace_root: Path, scope: str) -> Optional[Dict[str, Any]]:
    """G4: One-step rollback: restore last known good for scope. Returns restored config or None."""
    path = _lkg_path(workspace_root, scope)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("config")


def record_applied_change(
    workspace_root: Path,
    proposal_id: str,
    approved_by: str,
    canary_results: Optional[Dict[str, Any]] = None,
) -> None:
    """G5: Append to audit trail: who approved, when, canary results."""
    path = _audit_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "proposal_id": proposal_id,
        "approved_by": approved_by,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "canary_results": canary_results,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
