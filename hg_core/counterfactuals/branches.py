"""
Counterfactual branch recorder (Pack 2).
At decision proposal: record each option as a branch; store predictions per branch.
Events: COUNTERFACTUAL_BRANCH_RECORDED, COUNTERFACTUAL_PREDICTION_MADE.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.ledger import emit


def _iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def record_counterfactual_branch(
    *,
    decision_id: str,
    option_id: str,
    option_summary: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    notes: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Record an alternative option not chosen (at DECISION_PROPOSED time).
    Emit COUNTERFACTUAL_BRANCH_RECORDED. Returns branch_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    branch_id = "cfb_" + hashlib.sha256(
        f"{decision_id}:{option_id}:{ts}".encode()
    ).hexdigest()[:16]
    root = workspace_root / "artifacts" / "counterfactuals" / "branches"
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{branch_id}.json"
    artifact_path.write_text(
        json.dumps({
            "branch_id": branch_id,
            "decision_id": decision_id,
            "option_id": option_id,
            "option_summary": option_summary,
            "notes": notes or {},
            "ts": ts,
        }, indent=2),
        encoding="utf-8",
    )
    emit(
        "COUNTERFACTUAL_BRANCH_RECORDED",
        "counterfactual_branch",
        branch_id,
        {
            "branch_id": branch_id,
            "decision_id": decision_id,
            "option_id": option_id,
            "option_summary": option_summary,
            "artifact_id": str(artifact_path),
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return branch_id


def record_counterfactual_prediction(
    *,
    branch_id: str,
    decision_id: str,
    prediction_id: str,
    expected_outcome: Dict[str, Any],
    confidence: float,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
) -> str:
    """
    Record predicted outcome for a counterfactual branch.
    Emit COUNTERFACTUAL_PREDICTION_MADE. Returns event_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    return emit(
        "COUNTERFACTUAL_PREDICTION_MADE",
        "counterfactual_prediction",
        prediction_id,
        {
            "branch_id": branch_id,
            "decision_id": decision_id,
            "prediction_id": prediction_id,
            "expected_outcome": expected_outcome,
            "confidence": max(0.0, min(1.0, confidence)),
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
