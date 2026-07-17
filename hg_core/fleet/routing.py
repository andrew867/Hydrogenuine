"""
Control Surface Pack 10: Cross-swarm routing — suggest targets, apply with proof artifact.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from hg_core.swarms import list_swarms


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _materialized_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "materialized"


def _routing_artifacts_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "fleet" / "routing"


def suggest_routing(
    workspace_root: Path,
    work_item_id: str,
    from_swarm: str,
    constraints: Optional[List[str]] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Suggest routing targets for a work item. Returns { suggestions: [ { swarm_id, score, reason } ], constraints_checked }.
    Uses swarms list and simple scoring (prefer live swarms, lower drift).
    """
    workspace_root = Path(workspace_root)
    swarms = list_swarms(workspace_root, limit=limit * 2)
    root = _materialized_root(workspace_root)
    drift_by_swarm: Dict[str, float] = {}
    drift_path = root / "drift_scores.jsonl"
    if drift_path.exists():
        for line in drift_path.read_text(encoding="utf-8").strip().split("\n"):
            if not line:
                continue
            try:
                row = json.loads(line)
                sid = (row.get("subject_ref") or {}).get("swarm_id") or "default"
                drift_by_swarm[sid] = max(drift_by_swarm.get(sid, 0), row.get("score") or 0)
            except json.JSONDecodeError:
                continue

    suggestions: List[Dict[str, Any]] = []
    for s in swarms:
        sid = s.get("swarm_id") or ""
        if sid == from_swarm:
            continue
        state = (s.get("state") or "draft").lower()
        score = 1.0 if state == "live" else 0.5 if state == "staged" else 0.2
        drift = drift_by_swarm.get(sid, 0)
        score -= drift * 0.3
        suggestions.append({
            "swarm_id": sid,
            "name": s.get("name", sid),
            "score": max(0, min(1, score)),
            "reason": f"state={state}, drift={drift:.2f}",
        })
    suggestions.sort(key=lambda x: -x.get("score", 0))
    return {
        "suggestions": suggestions[:limit],
        "constraints_checked": constraints or [],
    }


def apply_routing(
    *,
    work_item_id: str,
    from_swarm: str,
    to_swarm: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    rationale_artifact_id: str = "",
    constraints_checked: Optional[List[str]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Route work item to target swarm. Emit WORK_ITEM_ROUTED, write routing proof artifact.
    Returns routing_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    routing_id = "route_" + hashlib.sha256(f"{work_item_id}:{from_swarm}:{to_swarm}:{ts}".encode()).hexdigest()[:16]

    root = _routing_artifacts_root(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    proof = {
        "routing_id": routing_id,
        "work_item_id": work_item_id,
        "from_swarm": from_swarm,
        "to_swarm": to_swarm,
        "ts": ts,
        "rationale_artifact_id": rationale_artifact_id or "",
        "constraints_checked": constraints_checked or [],
    }
    path = root / f"{routing_id}.json"
    path.write_text(json.dumps(proof, indent=2), encoding="utf-8")

    emit(
        "WORK_ITEM_ROUTED",
        "routing",
        routing_id,
        {
            "routing_id": routing_id,
            "work_item_id": work_item_id,
            "from_swarm": from_swarm,
            "to_swarm": to_swarm,
            "ts": ts,
            "rationale_artifact_id": rationale_artifact_id or "",
            "constraints_checked": constraints_checked or [],
            "artifact_path": str(path),
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return routing_id
