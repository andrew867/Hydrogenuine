"""
Layer 9 Phase 3: Regurgitation vs learned — metric/heuristic from attribution (few inputs -> regurgitation).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from hg_core.alignment_science.schemas import (
    regurgitation_vs_learned_result,
    RegurgitationVsLearnedResult,
    validate_regurgitation_vs_learned_result,
)


def _artifacts_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "alignment_science" / "regurgitation"


def _safe_decision_id(decision_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in decision_id)[:64]


def _label_from_influential_count(num_inputs: int) -> tuple[str, float]:
    """Heuristic: 0–1 inputs -> regurgitation, 2+ -> learned, with simple score."""
    if num_inputs <= 1:
        return "regurgitation", 0.2
    if num_inputs >= 4:
        return "learned", 0.8
    return "mixed", 0.5


def run_regurgitation_vs_learned(
    workspace_root: Path,
    decision_id: str,
    run_id: Optional[str] = None,
    emit_ledger: bool = True,
) -> RegurgitationVsLearnedResult:
    """
    Use attribution influential_inputs count (run attribution if missing) to set label/score;
    write RegurgitationVsLearnedResult artifact.
    """
    workspace_root = Path(workspace_root)
    from hg_core.alignment_science.attribution import get_attribution, run_attribution
    audit = get_attribution(workspace_root, decision_id)
    if audit is None:
        audit = run_attribution(workspace_root, decision_id, run_id=run_id, emit_ledger=False)
    num_inputs = len(audit.get("influential_inputs") or [])
    label, score = _label_from_influential_count(num_inputs)
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = _artifacts_root(workspace_root) / date_prefix
    root.mkdir(parents=True, exist_ok=True)
    safe_id = _safe_decision_id(decision_id)
    artifact_path = root / f"{safe_id}.json"
    result = regurgitation_vs_learned_result(
        decision_id=decision_id,
        label=label,
        artifact_ref=str(artifact_path),
        run_id=run_id,
        score=score,
    )
    artifact_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if emit_ledger:
        try:
            from hg_core.ledger import emit
            emit(
                "REGURGITATION_VS_LEARNED_RECORDED",
                "regurgitation",
                decision_id,
                {"decision_id": decision_id, "label": label, "score": score, "artifact_ref": str(artifact_path)},
                workspace_root=workspace_root,
                object_path=str(artifact_path),
            )
        except Exception:
            pass
    return result


def get_regurgitation_result(workspace_root: Path, decision_id: str) -> Optional[RegurgitationVsLearnedResult]:
    """Return RegurgitationVsLearnedResult for decision_id if stored; else None."""
    workspace_root = Path(workspace_root)
    root = _artifacts_root(workspace_root)
    if not root.exists():
        return None
    safe_id = _safe_decision_id(decision_id)
    for date_dir in sorted(root.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        path = date_dir / f"{safe_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("decision_id") == decision_id and validate_regurgitation_vs_learned_result(data):
                    return data
            except Exception:
                continue
    return None
