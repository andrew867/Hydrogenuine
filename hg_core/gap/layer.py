"""
Reality gap layer: quantify divergence between model and world.
Inputs: predictions vs evaluations, verifier disagreement, anomalies, overrides, tool failures.
Outputs: GAP_SCORE_COMPUTED, GAP_ALERT_RAISED, GAP_CONTROL_APPLIED.
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


def _load_ledger_events(workspace_root: Path):
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        yield ev


def compute_gap_score(
    *,
    subject_type: str,
    subject_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    prediction_error: float = 0.0,
    verifier_disagreement: float = 0.0,
    anomaly_rate: float = 0.0,
    override_rate: float = 0.0,
    tool_failure_rate: float = 0.0,
    evidence_refs: Optional[List[Dict[str, Any]]] = None,
) -> tuple[float, str]:
    """
    Compute gap score (0-1) from inputs; write rationale artifact; emit GAP_SCORE_COMPUTED.
    Returns (score, event_id).
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    # Weighted combination; clamp to [0, 1]
    score = min(1.0, max(0.0, (
        prediction_error * 0.3
        + verifier_disagreement * 0.25
        + anomaly_rate * 0.2
        + override_rate * 0.15
        + tool_failure_rate * 0.1
    )))
    gap_id = "gap_" + hashlib.sha256(
        f"{subject_type}:{subject_id}:{ts}".encode()
    ).hexdigest()[:16]
    root = workspace_root / "artifacts" / "gap"
    root.mkdir(parents=True, exist_ok=True)
    rationale_path = root / f"{gap_id}.json"
    rationale_path.write_text(
        json.dumps({
            "gap_id": gap_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "score": score,
            "prediction_error": prediction_error,
            "verifier_disagreement": verifier_disagreement,
            "anomaly_rate": anomaly_rate,
            "override_rate": override_rate,
            "tool_failure_rate": tool_failure_rate,
            "ts": ts,
        }, indent=2),
        encoding="utf-8",
    )
    payload = {
        "gap_id": gap_id,
        "subject_type": subject_type,
        "subject_id": subject_id,
        "score": score,
        "ts": ts,
        "evidence_refs": evidence_refs or [],
        "rationale_artifact_id": str(rationale_path),
    }
    event_id = emit(
        "GAP_SCORE_COMPUTED",
        "gap",
        gap_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return score, event_id


def raise_gap_alert(
    *,
    gap_id: str,
    threshold: float,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    recommended_controls: Optional[List[str]] = None,
) -> str:
    """Emit GAP_ALERT_RAISED when gap score crosses threshold. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {
        "gap_id": gap_id,
        "threshold": threshold,
        "ts": ts,
        "recommended_controls": recommended_controls or [],
    }
    return emit(
        "GAP_ALERT_RAISED",
        "gap",
        gap_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def apply_gap_control(
    *,
    gap_id: str,
    controls_applied: List[str],
    rationale_artifact_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit GAP_CONTROL_APPLIED when gating changes due to gap. Returns event_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    payload = {
        "gap_id": gap_id,
        "controls_applied": controls_applied,
        "rationale_artifact_id": rationale_artifact_id,
        "ts": ts,
    }
    return emit(
        "GAP_CONTROL_APPLIED",
        "gap",
        gap_id,
        payload,
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )


def get_gap_scores(
    workspace_root: Path,
    subject_type: Optional[str] = None,
    subject_id: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Return GAP_SCORE_COMPUTED events, optionally filtered. Most recent first."""
    out: List[Dict[str, Any]] = []
    for ev in _load_ledger_events(Path(workspace_root)):
        if ev.get("action") != "GAP_SCORE_COMPUTED":
            continue
        p = (ev.get("payload") or {}).copy()
        if subject_type and p.get("subject_type") != subject_type:
            continue
        if subject_id and p.get("subject_id") != subject_id:
            continue
        p["event_id"] = ev.get("event_id")
        p["ts"] = p.get("ts") or ev.get("ts")
        out.append(p)
    out.sort(key=lambda x: x.get("ts") or "", reverse=True)
    return out[:limit]
