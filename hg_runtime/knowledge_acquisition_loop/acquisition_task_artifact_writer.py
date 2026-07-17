"""P30-1 acquisition task artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_acquisition_task_artifacts(proof_dir: Path, layer: dict) -> None:
    write_json(proof_dir / "task_manifest.json", layer["manifest"])
    write_json(proof_dir / "policy.json", layer["policy"])
    write_jsonl(proof_dir / "candidates.jsonl", layer["candidates"])
    write_jsonl(proof_dir / "sources.jsonl", layer["sources"])
    write_jsonl(proof_dir / "tasks.jsonl", layer["tasks"])
