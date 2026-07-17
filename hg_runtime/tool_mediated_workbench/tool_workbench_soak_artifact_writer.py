"""P29-3 tool workbench soak artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_soak_artifacts(
    *,
    proof_dir: Path,
    soak: dict,
    mutation_probes: dict,
    redaction_audit: dict,
) -> None:
    write_json(proof_dir / "soak_manifest.json", soak["manifest"])
    write_jsonl(proof_dir / "soak_iterations.jsonl", soak["iterations"])
    write_json(proof_dir / "stable_hashes.json", soak["stable_hashes"])
    write_jsonl(proof_dir / "mutation_probes.jsonl", mutation_probes["probes"])
    write_jsonl(proof_dir / "mutation_results.jsonl", mutation_probes["results"])
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
