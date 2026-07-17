"""
Layer 9 Phase 3: Attribution pipeline — influential inputs for a decision (heuristic from proof-path).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.alignment_science.schemas import (
    attribution_result,
    AttributionResult,
    InfluentialInput,
    validate_attribution_result,
)


def _artifacts_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "artifacts" / "alignment_science" / "attribution"


def _safe_decision_id(decision_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in decision_id)[:64]


def _influential_inputs_from_proof_path(proof_path: Dict[str, Any]) -> List[InfluentialInput]:
    inputs: List[InfluentialInput] = []
    decision = proof_path.get("decision") or {}
    for i, cid in enumerate(decision.get("based_on_claim_ids") or []):
        inputs.append({"ref": cid, "type": "claim_id", "weight_or_rank": 1.0 - (i * 0.1)})
    if decision.get("event_id"):
        inputs.append({"ref": decision["event_id"], "type": "event_id", "weight_or_rank": 0.9})
    for i, aid in enumerate(decision.get("produced_artifact_ids") or []):
        inputs.append({"ref": aid, "type": "artifact_id", "weight_or_rank": 0.8 - (i * 0.05)})
    for r in proof_path.get("representation_inspection_result") or []:
        eid = r.get("event_id") or r.get("inspection_id")
        if eid and not any(inp.get("ref") == eid for inp in inputs):
            inputs.append({"ref": eid, "type": "inspection", "weight_or_rank": 0.7})
    return inputs


def run_attribution(
    workspace_root: Path,
    decision_id: str,
    run_id: Optional[str] = None,
    emit_ledger: bool = True,
) -> AttributionResult:
    workspace_root = Path(workspace_root)
    try:
        from hg_core.metacognition.proof_path import get_proof_path
        proof = get_proof_path(workspace_root, decision_id)
    except Exception:
        proof = {"decision_id": decision_id, "decision": {}}
    influential = _influential_inputs_from_proof_path(proof)
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = _artifacts_root(workspace_root) / date_prefix
    root.mkdir(parents=True, exist_ok=True)
    safe_id = _safe_decision_id(decision_id)
    artifact_path = root / f"{safe_id}.json"
    result = attribution_result(
        decision_id=decision_id,
        influential_inputs=influential,
        artifact_ref=str(artifact_path),
        run_id=run_id,
    )
    artifact_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if emit_ledger:
        try:
            from hg_core.ledger import emit
            emit(
                "ATTRIBUTION_RECORDED",
                "attribution",
                decision_id,
                {"decision_id": decision_id, "artifact_ref": str(artifact_path), "input_count": len(influential)},
                workspace_root=workspace_root,
                object_path=str(artifact_path),
            )
        except Exception:
            pass
    return result


def get_attribution(workspace_root: Path, decision_id: str) -> Optional[AttributionResult]:
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
                if data.get("decision_id") == decision_id and validate_attribution_result(data):
                    return data
            except Exception:
                continue
    return None
