"""P26-4 artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_p26_4_bundle(layer: dict, proof_dir: Path, summary: dict) -> None:
    write_json(proof_dir / "gate_result.json", summary)
    write_jsonl(proof_dir / "p26_recall_soak_iterations.jsonl", layer["soak"]["iterations"])
    write_json(proof_dir / "p26_stable_hashes.json", layer["soak"]["stable_hashes"])
    write_jsonl(proof_dir / "p26_mutation_probes.jsonl", layer["mutations"]["probes"])
    write_jsonl(proof_dir / "p26_mutation_results.jsonl", layer["mutations"]["results"])
    write_json(proof_dir / "p26_recall_soak_manifest.json", layer["soak"]["manifest"])
    write_json(proof_dir / "replay_result.json", layer["replay"])
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["receipt_chain"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": summary["secret_redaction_passed"]})
