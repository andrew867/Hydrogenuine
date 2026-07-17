"""Index proof bundles for SLE-RC audit."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.safe_local_evidence_rc.gate_status_reader import latest_gate_result
from hg_runtime.safe_local_evidence_rc.schemas import COMPONENT_CONSOLIDATION


def build_proof_bundle_index(root: Path) -> dict:
    entries = []
    for family, (proof_root, expected) in COMPONENT_CONSOLIDATION.items():
        verdict, proof_bundle, gate_data = latest_gate_result(root, proof_root)
        entries.append(
            {
                "component_family": family,
                "proof_root": proof_root,
                "expected_verdict": expected,
                "gate_verdict": verdict,
                "proof_bundle": proof_bundle,
                "is_green": verdict == expected and verdict.startswith("GREEN"),
                "base_head": gate_data.get("base_head", "") if gate_data else "",
            }
        )
    return {
        "entry_count": len(entries),
        "entries": entries,
        "all_green": all(row["is_green"] for row in entries),
    }
