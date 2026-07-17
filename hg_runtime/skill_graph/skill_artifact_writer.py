"""Write P27 skill extraction artifacts."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_p27_1_artifacts(proof_dir: Path, layer: dict) -> None:
    write_json(proof_dir / "p27_p26_memory_manifest.json", layer["manifest"])
    write_jsonl(proof_dir / "skill_records.jsonl", layer["skill_records"])
    write_jsonl(proof_dir / "skill_source_memory_links.jsonl", layer["skill_source_memory_links"])
    write_jsonl(proof_dir / "skill_extraction_rejections.jsonl", layer.get("skill_extraction_rejections", []))
    write_json(proof_dir / "recall_index_snapshot.json", layer["recall_index"]["index"])
    write_json(proof_dir / "replay_result.json", {"replay_deterministic": layer["replay_deterministic"]})
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["skill_records"] + layer["skill_source_memory_links"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": layer["secret_redaction_passed"]})
