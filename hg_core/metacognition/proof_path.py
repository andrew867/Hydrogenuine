"""
Proof-path: Decision -> Claims -> Values -> Context -> Artifacts -> Predictions -> Evaluations -> Self-assessments.
Export emits audit artifact and DECISION_AUDIT_EXPORTED.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.ledger import emit
from hg_core.ledger.facts_meaning import explain_decision


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def get_proof_path(workspace_root: Path, decision_id: str) -> Dict[str, Any]:
    """
    Return full proof path for a decision: decision (claims, values, context, artifacts), predictions, evaluations, self-assessments.
    Reads from materialized views and facts_meaning.
    """
    workspace_root = Path(workspace_root)
    root = workspace_root / "memory" / "materialized"
    decision_explained = explain_decision(decision_id, workspace_root)
    predictions = [r for r in _load_jsonl(root / "predictions.jsonl") if r.get("decision_id") == decision_id]
    pred_ids = {p.get("prediction_id") for p in predictions if p.get("prediction_id")}
    evaluations = [r for r in _load_jsonl(root / "evaluations.jsonl") if r.get("prediction_id") in pred_ids]
    self_assessments = [r for r in _load_jsonl(root / "self_assessments.jsonl") if r.get("decision_id") == decision_id]
    # Layer 8 Phase 3: include representation inspection results when present
    representation_inspection_result: List[Dict[str, Any]] = []
    try:
        from hg_core.repr_interp.storage import get_inspection_results
        representation_inspection_result = get_inspection_results(
            workspace_root, decision_id=decision_id
        )
    except Exception:
        pass
    return {
        "decision_id": decision_id,
        "decision": {
            "title": decision_explained.get("title", ""),
            "based_on_claim_ids": decision_explained.get("based_on_claim_ids", []),
            "value_weights": decision_explained.get("value_weights", []),
            "context_ref": decision_explained.get("context_ref", {}),
            "produced_artifact_ids": decision_explained.get("produced_artifact_ids", []),
            "event_id": decision_explained.get("event_id"),
        },
        "predictions": predictions,
        "evaluations": evaluations,
        "self_assessments": self_assessments,
        "representation_inspection_result": representation_inspection_result,
    }


def export_proof_path(
    workspace_root: Path,
    decision_id: str,
    *,
    scope: Optional[Dict[str, str]] = None,
    actor: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Build proof path, write to artifact (artifacts/metacognition/audit/<date>/<decision_id>_audit.json), emit DECISION_AUDIT_EXPORTED.
    Returns {proof_path, artifact_path, event_id}.
    """
    workspace_root = Path(workspace_root)
    proof = get_proof_path(workspace_root, decision_id)
    audit_dir = workspace_root / "artifacts" / "metacognition" / "audit"
    from datetime import datetime, timezone
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    audit_dir = audit_dir / date_prefix
    audit_dir.mkdir(parents=True, exist_ok=True)
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in decision_id)[:64]
    artifact_path = audit_dir / f"{safe_id}_audit.json"
    artifact_path.write_text(json.dumps(proof, indent=2, ensure_ascii=False), encoding="utf-8")
    scope = scope or {"type": "global", "id": "default"}
    actor = actor or {"agent_id": "operator", "pubkey": "", "key_id": ""}
    event_id = emit(
        "DECISION_AUDIT_EXPORTED",
        "audit_export",
        f"audit_{decision_id}",
        {"decision_id": decision_id, "artifact_path": str(artifact_path)},
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
        object_path=str(artifact_path),
    )
    # Layer 8 Phase 2: opt-in repr_interp capture on proof-path export
    try:
        from hg_core.repr_interp.capture import is_repr_interp_capture_enabled, capture_context
        if is_repr_interp_capture_enabled(workspace_root):
            capture_context(
                workspace_root,
                f"proof_path_{decision_id}",
                audit_dir,
                decision_id,
                "decision",
                context_ref={"decision_id": decision_id, "artifact_path": str(artifact_path), "event_id": event_id},
                event_id=event_id,
            )
    except Exception:
        pass
    return {"proof_path": proof, "artifact_path": str(artifact_path), "event_id": event_id}
