"""Map P29 workbench capability gaps and evidence gaps to acquisition candidates."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.tool_mediated_workbench.tool_plan_builder import build_tool_plan_layer


_GAP_TO_SOURCE_TYPE = {
    "file_write": "local_evidence",
    "file_delete": "local_evidence",
    "arbitrary_execution": "local_evidence",
    "live_web_access": "local_report",
    "live_provider_access": "local_report",
}

_EVIDENCE_SOURCE_TYPES = {
    "proof_bundle": "local_proof",
    "evidence_artifact": "local_evidence",
    "report": "local_report",
    "artifact": "local_evidence",
}


def map_workbench_gaps_to_candidates(repo_root: Path) -> dict:
    layer = build_tool_plan_layer(repo_root)
    candidates = []
    for i, gap in enumerate(layer.get("all_gaps", [])):
        gap_type = gap.get("gap_type", "unknown")
        source_type = _GAP_TO_SOURCE_TYPE.get(gap_type, "local_evidence")
        candidates.append({
            "candidate_id": f"cand-gap-{i:03d}",
            "description": f"Knowledge gap from workbench capability gap: {gap_type}",
            "source_type": source_type,
            "origin": "workbench_gap",
            "workbench_gap_ref": gap,
        })
    return {
        "workbench_gap_candidates": candidates,
        "workbench_layer": layer,
    }


def map_evidence_gaps_to_candidates(repo_root: Path) -> list[dict]:
    evidence_dir = repo_root / "docs" / "proofs" / "autonomous_agent_zero"
    candidates = []
    if evidence_dir.exists():
        existing_proofs = sorted(d.name for d in evidence_dir.iterdir() if d.is_dir())
        for i, proof_name in enumerate(existing_proofs[:5]):
            candidates.append({
                "candidate_id": f"cand-evidence-{i:03d}",
                "description": f"Evidence artifact from proof: {proof_name}",
                "source_type": "local_proof",
                "origin": "evidence_gap",
                "proof_ref": proof_name,
            })
    return candidates
