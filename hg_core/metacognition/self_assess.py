"""
Self-assessment: record confidence, uncertainty, risk flags, recommended controls; emit SELF_ASSESSMENT_RECORDED.
Rationale is stored as artifact; self-reports cannot grant power (policy decides gating).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from .artifacts import write_rationale


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def record_self_assessment(
    *,
    decision_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    confidence: float,
    uncertainty_factors: List[str],
    risk_flags: List[str],
    recommended_controls: Dict[str, Any],
    rationale_artifact_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Publish self-assessment rationale artifact and emit SELF_ASSESSMENT_RECORDED.
    recommended_controls must include require_approval and slow_mode (booleans); optional escrow_amount.
    Returns assessment_id. Self-reports do not directly change trust/budget; policy decides.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    assessment_id = rationale_artifact_id or hashlib.sha256(f"{decision_id}:{ts}".encode()).hexdigest()
    rationale = {
        "assessment_id": assessment_id,
        "decision_id": decision_id,
        "ts": ts,
        "confidence": confidence,
        "uncertainty_factors": uncertainty_factors,
        "risk_flags": risk_flags,
        "recommended_controls": recommended_controls,
        "notes": notes or "",
    }
    write_rationale(workspace_root, assessment_id, rationale, subdir="self_assessment")
    rc = recommended_controls or {}
    if "require_approval" not in rc:
        rc = dict(rc)
        rc["require_approval"] = False
    if "slow_mode" not in rc:
        rc = dict(rc)
        rc["slow_mode"] = False
    emit(
        "SELF_ASSESSMENT_RECORDED",
        "self_assessment",
        assessment_id,
        {
            "assessment_id": assessment_id,
            "decision_id": decision_id,
            "confidence": max(0.0, min(1.0, confidence)),
            "uncertainty_factors": list(uncertainty_factors or []),
            "risk_flags": list(risk_flags or []),
            "recommended_controls": rc,
            "rationale_artifact_id": assessment_id,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return assessment_id
