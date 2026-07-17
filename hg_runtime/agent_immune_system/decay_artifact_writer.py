"""AIS-5 cruft/decay proof artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.agent_immune_system.artifact_writer import write_json, write_jsonl


def write_decay_artifacts(layer: dict, proof_dir: Path) -> None:
    write_json(proof_dir / "cruft_decay_manifest.json", layer["manifest"])
    write_jsonl(proof_dir / "cruft_decay_findings.jsonl", layer["findings"])
    write_json(proof_dir / "cruft_decay_replay_record.json", layer["replay"])
