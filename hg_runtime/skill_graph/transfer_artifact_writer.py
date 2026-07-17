"""Write P27 transfer graph artifacts."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_p27_2_artifacts(proof_dir: Path, layer: dict) -> None:
    write_json(proof_dir / "skill_graph_index.json", layer["skill_graph_index"])
    write_jsonl(proof_dir / "skill_edges.jsonl", layer["skill_edges"])
    write_jsonl(proof_dir / "transfer_candidates.jsonl", layer["transfer_candidates"])
    write_json(proof_dir / "transfer_candidate_manifest.json", layer["transfer_candidate_manifest"])
    write_json(proof_dir / "replay_result.json", {"replay_deterministic": layer["replay_deterministic"]})
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["skill_records"] + layer["skill_edges"] + layer["transfer_candidates"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": layer["secret_redaction_passed"]})
