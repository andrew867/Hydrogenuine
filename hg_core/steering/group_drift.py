"""
Control Surface Pack 7: Group-level drift — scores across swarm, correlated erosion, safeguards.
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
        except json.JSONDecodeError:
            continue
    return out


def compute_group_drift_score(
    *,
    synchronized_autonomy_increases: int = 0,
    correlated_constraint_erosion: bool = False,
    high_impact_proposals_count: int = 0,
    verifier_monoculture_risk: bool = False,
) -> float:
    """Compute GROUP_DRIFT_SCORE 0..1 from swarm-level signals."""
    score = 0.0
    if synchronized_autonomy_increases:
        score += min(0.4, 0.15 * synchronized_autonomy_increases)
    if correlated_constraint_erosion:
        score += 0.3
    if high_impact_proposals_count:
        score += min(0.3, 0.1 * high_impact_proposals_count)
    if verifier_monoculture_risk:
        score += 0.2
    return min(1.0, score)


def emit_group_drift_score(
    *,
    group_id: str,
    score: float,
    scope: Dict[str, str],
    actor: Dict[str, str],
    rationale_artifact_id: str = "",
    signals: Optional[List[Dict[str, Any]]] = None,
    evidence_refs: Optional[List[Dict[str, str]]] = None,
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit GROUP_DRIFT_SCORE_COMPUTED. Returns gd_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    gd_id = "gd_" + hashlib.sha256(f"{group_id}:{ts}".encode()).hexdigest()[:16]
    payload: Dict[str, Any] = {
        "gd_id": gd_id,
        "group_id": group_id,
        "score": score,
        "ts": ts,
        "rationale_artifact_id": rationale_artifact_id or "",
        "evidence_refs": evidence_refs or [],
    }
    if signals:
        payload["signals"] = signals
    emit(
        "GROUP_DRIFT_SCORE_COMPUTED",
        "group_drift",
        gd_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return gd_id


def get_group_drift_scores(
    workspace_root: Path,
    group_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Load group drift scores from materialized group_drift_scores.jsonl."""
    root = _materialized_root(workspace_root)
    rows = _load_jsonl(root / "group_drift_scores.jsonl")
    if group_id:
        rows = [r for r in rows if r.get("group_id") == group_id]
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return rows[:limit]


def get_group_drift_alerts(workspace_root: Path) -> List[Dict[str, Any]]:
    """Active group drift safeguards (GROUP_SAFEGUARD_APPLIED)."""
    root = _materialized_root(workspace_root)
    return _load_jsonl(root / "group_drift_alerts.jsonl")
