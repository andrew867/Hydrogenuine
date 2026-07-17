"""Map P26 acceptance criteria onto existing runtime artifacts (read-only)."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.generalist_gap_reconciliation.schemas import assert_neutral, neutral_flags, record_hash

# criterion id -> (list of proof roots that bear on it, list of module refs).
_CRITERION_ARTIFACTS = {
    "P26-AC-1": (["LEB-LOCAL-EVIDENCE-BRIDGE-CONSOLIDATION"], ["hg_runtime/memory_ledger/hash_chain.py", "hg_runtime/local_evidence_bridge"]),
    "P26-AC-2": (["SQP-SOURCE-QUALITY-PROVENANCE-CONSOLIDATION"], ["hg_runtime/source_quality_provenance/provenance_graph_builder.py"]),
    "P26-AC-3": (["SLE-RC-EXTENDED-REGRESSION-SOAK", "SLE-SAFE-LOCAL-EVIDENCE-RELEASE-CANDIDATE"], ["hg_runtime/safe_local_evidence_rc/rc_replay.py"]),
    "P26-AC-4": (["LEB-7-EVIDENCE-RETRACTION-QUARANTINE"], ["hg_runtime/local_evidence_bridge/evidence_quarantine_loop.py"]),
    "P26-AC-5": ([], []),
    "P26-AC-6": (["REVIEWED-LOCAL-EVIDENCE-BETA"], ["hg_runtime/operator_review_promotion"]),
    "P26-AC-7": (["WMBR-06-WORLD-MODEL-AUDIT"], ["hg_runtime/local_evidence_bridge/evidence_decay.py"]),
    "P26-AC-8": ([], []),
    "P26-AC-9": ([], []),
    "P26-AC-10": ([], []),
}


def _proof_present(root: Path, proof_root_name: str) -> dict:
    proof_root = root / "docs/proofs/autonomous_agent_zero" / proof_root_name
    gates = sorted(proof_root.glob("*/gate_result.json"))
    if not gates:
        return {"proof_root": proof_root_name, "present": False, "verdict": "UNKNOWN", "proof_bundle": ""}
    data = json.loads(gates[-1].read_text(encoding="utf-8"))
    return {
        "proof_root": proof_root_name,
        "present": True,
        "verdict": data.get("verdict", "UNKNOWN"),
        "proof_bundle": str(gates[-1].parent.relative_to(root)),
    }


def build_existing_artifact_map(root: Path) -> list[dict]:
    entries = []
    for criterion_id, (proof_roots, module_refs) in _CRITERION_ARTIFACTS.items():
        proofs = [_proof_present(root, name) for name in proof_roots]
        any_present = any(p["present"] for p in proofs)
        entry = {
            "schema_version": "1",
            "record_type": "p26_existing_artifact_map_entry_v1",
            "criterion_id": criterion_id,
            "mapped_proof_roots": proof_roots,
            "module_refs": module_refs,
            "proof_status": proofs,
            "any_artifact_present": any_present,
            "artifact_count": len(proof_roots),
            "existing_artifact_auto_completes_p26": False,
            **neutral_flags(),
        }
        entry["record_hash"] = record_hash(entry)
        assert_neutral(entry)
        entries.append(entry)
    return entries
