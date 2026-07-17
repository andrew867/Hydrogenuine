"""P26-3 artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_p26_3_bundle(layer: dict, proof_dir: Path, summary: dict) -> None:
    write_json(proof_dir / "gate_result.json", summary)
    write_jsonl(proof_dir / "memory_promotion_requests.jsonl", layer["requests"])
    write_jsonl(proof_dir / "memory_promotion_decisions.jsonl", layer["decisions"])
    write_jsonl(proof_dir / "memory_promotion_rejections.jsonl", layer["rejections"])
    write_json(proof_dir / "orp_memory_bridge_manifest.json", layer["manifest"])
    write_json(proof_dir / "replay_result.json", layer["replay"])
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["receipt_chain"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": summary["secret_redaction_passed"]})
