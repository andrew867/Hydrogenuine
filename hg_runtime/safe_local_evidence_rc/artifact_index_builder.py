"""Build SLE-RC artifact index from live proof bundles."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.safe_local_evidence_rc.gate_status_reader import latest_gate_result
from hg_runtime.safe_local_evidence_rc.proof_bundle_indexer import build_proof_bundle_index
from hg_runtime.safe_local_evidence_rc.rc_artifact_index import build_rc_artifact_index
from hg_runtime.safe_local_evidence_rc.report_indexer import COMPONENT_REPORTS, build_report_index
from hg_runtime.safe_local_evidence_rc.schemas import COMPONENT_CONSOLIDATION


def build_artifact_index(root: Path) -> dict:
    entries = []
    for family, (proof_root, expected) in COMPONENT_CONSOLIDATION.items():
        verdict, proof_bundle, gate_data = latest_gate_result(root, proof_root)
        report_path = COMPONENT_REPORTS.get(family, "")
        entries.append(
            {
                "component_family": family,
                "proof_root": proof_root,
                "expected_verdict": expected,
                "gate_verdict": verdict,
                "proof_bundle": proof_bundle,
                "report_path": report_path,
                "report_exists": (root / report_path).exists() if report_path else False,
                "is_green": verdict == expected and verdict.startswith("GREEN"),
                "base_head": gate_data.get("base_head", "") if gate_data else "",
            }
        )
    index = build_rc_artifact_index(index_id="rc-artifact-index-v1", entries=entries)
    return {
        "rc_artifact_index": index,
        "entries": entries,
        "proof_bundle_index": build_proof_bundle_index(root),
        "report_index": build_report_index(root),
        "all_consolidations_green": all(row["is_green"] for row in entries),
    }
