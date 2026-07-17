"""AIS-3 quarantine proof artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.agent_immune_system.artifact_writer import write_json, write_jsonl


def write_quarantine_artifacts(layer: dict, proof_dir: Path) -> None:
    write_json(proof_dir / "quarantine_manifest.json", layer["manifest"])
    write_jsonl(proof_dir / "quarantine_records.jsonl", layer["records"])
    write_jsonl(proof_dir / "quarantine_review_tasks.jsonl", layer["review_tasks"])
    write_json(proof_dir / "quarantine_replay_record.json", layer["replay"])
