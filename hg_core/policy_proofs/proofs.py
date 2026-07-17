"""
Policy proofs: policy evaluation creates machine-checkable proof (policy version, rule ids, inputs, decision, evidence_refs).
Stored as artifacts; exportable in offline bundles.
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


def create_proof(
    *,
    policy_artifact_id: str,
    rule_ids: List[str],
    inputs: Dict[str, Any],
    decision: Dict[str, Any],
    evidence_refs: List[Dict[str, Any]],
    scope: Optional[Dict[str, str]] = None,
    actor: Optional[Dict[str, str]] = None,
    workspace_root: Optional[Path] = None,
    emit_event: bool = True,
) -> str:
    """
    Create and store a policy evaluation proof. Returns proof_id.
    Proof includes policy_artifact_id, rule_ids, inputs, decision, evidence_refs, ts.
    """
    workspace_root = Path(workspace_root or ".")
    ts = _iso_ts()
    proof_id = "proof_" + hashlib.sha256(
        f"{policy_artifact_id}:{','.join(rule_ids)}:{ts}".encode()
    ).hexdigest()[:16]
    proof = {
        "proof_id": proof_id,
        "policy_artifact_id": policy_artifact_id,
        "rule_ids": list(rule_ids),
        "inputs": inputs,
        "decision": decision,
        "evidence_refs": list(evidence_refs),
        "ts": ts,
    }
    root = workspace_root / "artifacts" / "policy_proofs"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{proof_id}.json"
    path.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    if emit_event:
        emit(
            "POLICY_PROOF_RECORDED",
            "policy_proof",
            proof_id,
            {"proof_id": proof_id, "artifact_path": str(path), "ts": ts},
            scope=scope or {"type": "global", "id": "default"},
            actor=actor,
            workspace_root=workspace_root,
        )
    return proof_id


def get_proof(
    proof_id: str,
    workspace_root: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Load proof by proof_id from artifacts/policy_proofs. Returns None if not found."""
    workspace_root = Path(workspace_root or ".")
    path = workspace_root / "artifacts" / "policy_proofs" / f"{proof_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def evaluate_with_proof(
    engine: Any,
    ctx: Dict[str, Any],
    *,
    policy_artifact_id: str,
    scope: Optional[Dict[str, str]] = None,
    actor: Optional[Dict[str, str]] = None,
    workspace_root: Optional[Path] = None,
) -> tuple[Dict[str, Any], str]:
    """
    Call policy engine evaluate(ctx), then create a proof. Returns (evaluate_result, proof_id).
    rule_ids are derived from rationale keys (trust_band, action_cost, require_approval_reason, deny_reason, etc.).
    """
    result = engine.evaluate(ctx)
    rationale = result.get("rationale") or {}
    rule_ids = ["trust_band", "action_cost"]
    if rationale.get("deny_reason"):
        rule_ids.append("deny_reason")
    if rationale.get("require_approval_reason"):
        rule_ids.append("require_approval_reason")
    proof_id = create_proof(
        policy_artifact_id=policy_artifact_id,
        rule_ids=rule_ids,
        inputs=ctx,
        decision=result,
        evidence_refs=[{"rationale": rationale}],
        scope=scope,
        actor=actor,
        workspace_root=workspace_root,
        emit_event=True,
    )
    return result, proof_id
