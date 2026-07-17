"""Control Surface Pack 6: Drift scoring and DRIFT_SCORE_COMPUTED emission."""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def compute_drift_scores(features: Dict[str, Any], kind: str = "human_intent") -> float:
    """Compute drift score 0..1 from features. kind: human_intent | agent_response."""
    factors = features.get("factors") or []
    total = sum(f.get("weight", 0) for f in factors)
    if kind == "agent_response":
        total *= 1.2
    return min(1.0, total)


def emit_drift_score(
    kind: str,
    subject_ref: Dict[str, Any],
    thread_id: str,
    score: float,
    scope: Dict[str, str],
    actor: Dict[str, str],
    work_item_id: str = "",
    factors: Optional[List[Dict[str, Any]]] = None,
    rationale_artifact_id: str = "",
    evidence_refs: Optional[List[Dict[str, str]]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit DRIFT_SCORE_COMPUTED. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    drift_id = "drift_" + hashlib.sha256(f"{kind}:{thread_id}:{ts}".encode()).hexdigest()[:16]
    payload: Dict[str, Any] = {
        "drift_id": drift_id,
        "kind": kind,
        "subject_ref": subject_ref,
        "thread_id": thread_id,
        "score": score,
        "ts": ts,
        "rationale_artifact_id": rationale_artifact_id or "",
        "evidence_refs": evidence_refs or [],
    }
    if work_item_id:
        payload["work_item_id"] = work_item_id
    if factors:
        payload["factors"] = factors
    return emit(
        "DRIFT_SCORE_COMPUTED",
        "drift_score",
        drift_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
