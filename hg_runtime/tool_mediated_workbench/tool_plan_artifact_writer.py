"""P29-1 tool plan artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_tool_plan_artifacts(
    *,
    proof_dir: Path,
    layer: dict,
    replay_result: dict,
    redaction_audit: dict,
) -> None:
    write_json(proof_dir / "layer_manifest.json", layer["manifest"])
    write_json(proof_dir / "p28_manifest.json", layer["p28_manifest"])
    write_jsonl(proof_dir / "tool_plans.jsonl", layer["plans"])
    write_jsonl(proof_dir / "tool_requests.jsonl", layer["requests"])
    write_json(proof_dir / "capability_gaps.json", {"gaps": layer["capability_gaps"]})
    write_json(proof_dir / "replay_result.json", replay_result)
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
