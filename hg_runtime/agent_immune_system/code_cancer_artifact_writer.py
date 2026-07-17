"""AIS-4 code cancer proof artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.agent_immune_system.artifact_writer import write_json, write_jsonl


def write_code_cancer_artifacts(layer: dict, proof_dir: Path) -> None:
    write_json(proof_dir / "code_cancer_manifest.json", layer["manifest"])
    write_jsonl(proof_dir / "code_cancer_findings.jsonl", layer["findings"])
    write_json(proof_dir / "code_cancer_replay_record.json", layer["replay"])
