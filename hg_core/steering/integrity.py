"""
Control Surface Pack 7: Goal integrity scoring — detect quiet redefinition, constraint erosion, alerts.
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


def _materialized_root(workspace_root: Path) -> Path:
    return workspace_root / "memory" / "materialized"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def compute_goal_integrity_score(
    *,
    old_goal: Optional[str] = None,
    new_goal: str,
    old_constraints: Optional[List[str]] = None,
    new_constraints: Optional[List[str]] = None,
    rationale_provided: bool = False,
    exceptions_count: int = 0,
    work_item_goal_aligned: bool = True,
) -> float:
    """
    Compute GOAL_INTEGRITY_SCORE 0..1. Lower = more risk (drift, erosion, misalignment).
    """
    score = 1.0
    if not rationale_provided and (old_goal != new_goal or (old_constraints != new_constraints)):
        score -= 0.3
    if old_constraints and new_constraints and len(new_constraints) < len(old_constraints):
        score -= 0.25  # constraint erosion
    if exceptions_count > 2:
        score -= 0.2  # exceptions as de-facto policy
    if not work_item_goal_aligned:
        score -= 0.25
    return max(0.0, min(1.0, score))


def emit_goal_integrity_score(
    *,
    target_ref: Dict[str, Any],
    work_item_id: str,
    score: float,
    scope: Dict[str, str],
    actor: Dict[str, str],
    rationale_artifact_id: str = "",
    factors: Optional[List[Dict[str, Any]]] = None,
    evidence_refs: Optional[List[Dict[str, str]]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit GOAL_INTEGRITY_SCORE_COMPUTED. Returns gi_id (event object_id)."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    gi_id = "gi_" + hashlib.sha256(
        f"{target_ref.get('id','')}:{work_item_id}:{ts}".encode()
    ).hexdigest()[:16]
    payload: Dict[str, Any] = {
        "gi_id": gi_id,
        "target_ref": target_ref,
        "work_item_id": work_item_id,
        "score": score,
        "ts": ts,
        "rationale_artifact_id": rationale_artifact_id or "",
        "evidence_refs": evidence_refs or [],
    }
    if factors:
        payload["factors"] = factors
    emit(
        "GOAL_INTEGRITY_SCORE_COMPUTED",
        "goal_integrity",
        gi_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return gi_id


def emit_goal_integrity_alert(
    *,
    target_ref: Dict[str, Any],
    work_item_id: str,
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit GOAL_INTEGRITY_ALERT_RAISED; may create GOAL_INTEGRITY_REVIEW_REQUIRED (WorkItem). Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "GOAL_INTEGRITY_ALERT_RAISED",
        "goal_integrity",
        work_item_id or "alert_" + ts[:10],
        {
            "target_ref": target_ref,
            "work_item_id": work_item_id,
            "reason": reason,
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def get_goal_integrity_scores(
    workspace_root: Path,
    target_id: Optional[str] = None,
    work_item_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Load goal integrity scores from materialized goal_integrity_scores.jsonl."""
    root = _materialized_root(workspace_root)
    rows = _load_jsonl(root / "goal_integrity_scores.jsonl")
    if target_id:
        rows = [r for r in rows if (r.get("target_ref") or {}).get("id") == target_id]
    if work_item_id:
        rows = [r for r in rows if r.get("work_item_id") == work_item_id]
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return rows[:limit]


def get_goal_integrity_alerts(workspace_root: Path) -> List[Dict[str, Any]]:
    """Active goal integrity alerts (review required)."""
    root = _materialized_root(workspace_root)
    return _load_jsonl(root / "goal_integrity_alerts.jsonl")
