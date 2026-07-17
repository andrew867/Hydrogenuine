"""
Regret calculator (Pack 2). After EVALUATION_RECORDED:
compute regret vs best predicted alternative, publish lesson artifact, emit REGRET_COMPUTED.
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


def compute_regret(
    *,
    decision_id: str,
    baseline_branch_id: str,
    actual_outcome: Dict[str, Any],
    predicted_best_outcome: Dict[str, Any],
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    score_override: Optional[float] = None,
) -> tuple[float, str, str]:
    """
    Compute regret score (e.g. difference or normalized loss vs predicted best).
    Write rationale artifact, emit REGRET_COMPUTED. Returns (score, event_id, regret_id).
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    if score_override is not None:
        score = float(score_override)
    else:
        # Simple numeric diff if both have a "value" key; else 0
        av = actual_outcome.get("value") if isinstance(actual_outcome.get("value"), (int, float)) else 0
        pv = predicted_best_outcome.get("value") if isinstance(predicted_best_outcome.get("value"), (int, float)) else 0
        score = max(0.0, float(pv - av))  # regret = how much better the alternative would have been
    regret_id = "regret_" + hashlib.sha256(
        f"{decision_id}:{baseline_branch_id}:{ts}".encode()
    ).hexdigest()[:16]
    root = workspace_root / "artifacts" / "counterfactuals" / "regret"
    root.mkdir(parents=True, exist_ok=True)
    rationale_path = root / f"{regret_id}.json"
    rationale_path.write_text(
        json.dumps({
            "regret_id": regret_id,
            "decision_id": decision_id,
            "baseline_branch_id": baseline_branch_id,
            "score": score,
            "actual_outcome": actual_outcome,
            "predicted_best_outcome": predicted_best_outcome,
            "ts": ts,
        }, indent=2),
        encoding="utf-8",
    )
    event_id = emit(
        "REGRET_COMPUTED",
        "regret",
        regret_id,
        {
            "regret_id": regret_id,
            "decision_id": decision_id,
            "score": score,
            "baseline_branch_id": baseline_branch_id,
            "ts": ts,
            "rationale_artifact_id": str(rationale_path),
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
    return score, event_id, regret_id


def publish_counterfactual_lesson(
    *,
    decision_id: str,
    regret_id: str,
    lesson_summary: str,
    scope: Dict[str, str],
    actor: Dict[str, str],
    workspace_root: Optional[Path] = None,
    lesson_notes: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Publish lesson artifact after regret computation. Emit COUNTERFACTUAL_LESSON_PUBLISHED.
    Returns event_id.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    lesson_id = "lesson_" + hashlib.sha256(
        f"{decision_id}:{regret_id}:{ts}".encode()
    ).hexdigest()[:16]
    root = workspace_root / "artifacts" / "counterfactuals" / "lessons"
    root.mkdir(parents=True, exist_ok=True)
    artifact_path = root / f"{lesson_id}.json"
    artifact_path.write_text(
        json.dumps({
            "lesson_id": lesson_id,
            "decision_id": decision_id,
            "regret_id": regret_id,
            "lesson_summary": lesson_summary,
            "lesson_notes": lesson_notes or {},
            "ts": ts,
        }, indent=2),
        encoding="utf-8",
    )
    return emit(
        "COUNTERFACTUAL_LESSON_PUBLISHED",
        "counterfactual_lesson",
        lesson_id,
        {
            "lesson_id": lesson_id,
            "decision_id": decision_id,
            "regret_id": regret_id,
            "lesson_summary": lesson_summary,
            "artifact_id": str(artifact_path),
            "ts": ts,
        },
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
    )
