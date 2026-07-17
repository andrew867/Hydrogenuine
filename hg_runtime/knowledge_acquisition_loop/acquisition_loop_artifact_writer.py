"""P30-2 acquisition loop artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_acquisition_loop_artifacts(proof_dir: Path, layer: dict) -> None:
    write_json(proof_dir / "loop_manifest.json", layer["manifest"])
    write_jsonl(proof_dir / "results.jsonl", layer["results"])
    write_jsonl(proof_dir / "refusals.jsonl", layer["refusals"])
    write_jsonl(proof_dir / "operator_reviews.jsonl", layer["operator_reviews"])
    if layer["unsourced_normalized"]:
        write_jsonl(proof_dir / "unsourced_normalized.jsonl", layer["unsourced_normalized"])
