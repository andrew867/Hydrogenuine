"""Write P28-3 domain pack soak artifacts."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_p28_3_artifacts(proof_dir: Path, layer: dict) -> None:
    write_jsonl(proof_dir / "domain_pack_soak_iterations.jsonl", layer["iterations"])
    write_json(proof_dir / "domain_pack_stable_hashes.json", layer["stable_hashes"])
    write_json(proof_dir / "domain_pack_soak_manifest.json", layer["manifest"])
    write_jsonl(proof_dir / "domain_pack_mutation_probes.jsonl", layer["mutation_probes"])
    write_jsonl(proof_dir / "domain_pack_mutation_results.jsonl", layer["mutation_results"])
    write_json(proof_dir / "replay_result.json", {"replay_deterministic": layer["all_iterations_match"]})
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["iterations"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": layer["secret_redaction_passed"]})
