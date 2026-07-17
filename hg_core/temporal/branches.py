"""
Counterfactual branches: BRANCH_PROPOSED, BRANCH_PREDICTION_MADE, BRANCH_CLOSED.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit
from .artifacts import write_branch_notes


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def propose_branch(
    *,
    decision_id: str,
    option_id: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    notes: str = "",
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit BRANCH_PROPOSED (optional notes artifact). Returns branch_id."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    branch_id = hashlib.sha256(f"{decision_id}:{option_id}:{ts}".encode()).hexdigest()
    notes_artifact_id = branch_id
    if notes:
        write_branch_notes(workspace_root, branch_id, {"branch_id": branch_id, "notes": notes, "ts": ts, "decision_id": decision_id})
    emit(
        "BRANCH_PROPOSED",
        "branch",
        branch_id,
        {"branch_id": branch_id, "decision_id": decision_id, "option_id": option_id, "notes_artifact_id": notes_artifact_id, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return branch_id


def record_branch_prediction(
    *,
    branch_id: str,
    decision_id: str,
    option_id: str,
    prediction_id: str,
    metric: Dict[str, Any],
    expected: Dict[str, Any],
    deadline: str,
    confidence: float,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """Emit BRANCH_PREDICTION_MADE. Returns event_id from emit."""
    workspace_root = Path(workspace_root or ".")
    emit(
        "BRANCH_PREDICTION_MADE",
        "branch_prediction",
        prediction_id,
        {
            "branch_id": branch_id,
            "decision_id": decision_id,
            "option_id": option_id,
            "prediction_id": prediction_id,
            "metric": metric,
            "expected": expected,
            "deadline": deadline,
            "confidence": max(0.0, min(1.0, confidence)),
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return prediction_id


def close_branch(
    *,
    branch_id: str,
    decision_id: str,
    reason: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> None:
    """Emit BRANCH_CLOSED."""
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    emit(
        "BRANCH_CLOSED",
        "branch",
        branch_id,
        {"branch_id": branch_id, "decision_id": decision_id, "reason": reason, "ts": ts},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
