"""P29-2 dry run artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_dry_run_artifacts(
    *,
    proof_dir: Path,
    layer: dict,
    replay_result: dict,
    redaction_audit: dict,
) -> None:
    write_json(proof_dir / "layer_manifest.json", layer["manifest"])
    write_jsonl(proof_dir / "sandbox_results.jsonl", layer["sandbox_results"])
    write_jsonl(proof_dir / "refusals.jsonl", layer["refusals"])
    write_jsonl(proof_dir / "receipts.jsonl", layer["receipts"])
    write_json(proof_dir / "replay_result.json", replay_result)
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
