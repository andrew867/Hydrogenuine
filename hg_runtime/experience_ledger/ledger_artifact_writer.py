"""P26 ledger artifact writer helpers."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_p26_1_bundle(layer: dict, proof_dir: Path, summary: dict) -> None:
    write_json(proof_dir / "gate_result.json", summary)
    write_jsonl(proof_dir / "experience_records.jsonl", layer["experience_records"])
    write_jsonl(proof_dir / "memory_records.jsonl", layer["memory_records"])
    write_json(proof_dir / "ledger_manifest.json", layer["ledger_manifest"])
    write_jsonl(proof_dir / "ledger_hash_chain.jsonl", layer["ledger_hash_chain"])
    write_jsonl(proof_dir / "artifact_memory_map.jsonl", layer["artifact_memory_map"])
    write_json(proof_dir / "explicit_artifact_manifest.json", layer["artifact_manifest"])
    write_json(proof_dir / "replay_result.json", layer["replay"])
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["receipt_chain"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": summary["secret_redaction_passed"]})

