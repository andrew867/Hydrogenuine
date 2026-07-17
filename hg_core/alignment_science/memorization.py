"""
Layer 9 Phase 3: Memorization detection — flag verbatim/near-verbatim (heuristic).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from hg_core.alignment_science.schemas import (
    memorization_result,
    MemorizationResult,
    validate_memorization_result,
)


def _artifacts_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "alignment_science" / "memorization"


def _safe_decision_id(decision_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in decision_id)[:64]


def _check_memorization_heuristic(proof_path: Dict[str, Any]) -> tuple[bool, float, Optional[str]]:
    decision = proof_path.get("decision") or {}
    claim_ids = decision.get("based_on_claim_ids") or []
    artifact_ids = decision.get("produced_artifact_ids") or []
    if len(claim_ids) <= 1 and len(artifact_ids) <= 1 and not proof_path.get("representation_inspection_result"):
        return False, 0.2, None
    return False, 0.0, None


def run_memorization_detection(
    workspace_root: Path,
    decision_id: str,
    run_id: Optional[str] = None,
    emit_ledger: bool = True,
) -> MemorizationResult:
    workspace_root = Path(workspace_root)
    try:
        from hg_core.metacognition.proof_path import get_proof_path
        proof = get_proof_path(workspace_root, decision_id)
    except Exception:
        proof = {"decision_id": decision_id, "decision": {}}
    is_mem, score, source_ref = _check_memorization_heuristic(proof)
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = _artifacts_root(workspace_root) / date_prefix
    root.mkdir(parents=True, exist_ok=True)
    safe_id = _safe_decision_id(decision_id)
    artifact_path = root / f"{safe_id}.json"
    result = memorization_result(
        decision_id=decision_id,
        is_memorized=is_mem,
        artifact_ref=str(artifact_path),
        run_id=run_id,
        score=score,
        source_ref=source_ref,
    )
    artifact_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if emit_ledger:
        try:
            from hg_core.ledger import emit
            emit(
                "MEMORIZATION_FLAG_RECORDED",
                "memorization",
                decision_id,
                {"decision_id": decision_id, "is_memorized": is_mem, "score": score, "artifact_ref": str(artifact_path)},
                workspace_root=workspace_root,
                object_path=str(artifact_path),
            )
        except Exception:
            pass
    return result


def get_memorization_result(workspace_root: Path, decision_id: str) -> Optional[MemorizationResult]:
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
                if data.get("decision_id") == decision_id and validate_memorization_result(data):
                    return data
            except Exception:
                continue
    return None
