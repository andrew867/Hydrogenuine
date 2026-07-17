"""AIS-7 patch hygiene proof artifact writer."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.agent_immune_system.artifact_writer import write_json, write_jsonl


def write_patch_hygiene_artifacts(layer: dict, proof_dir: Path) -> None:
    write_json(proof_dir / "patch_hygiene_manifest.json", layer["manifest"])
    write_jsonl(proof_dir / "patch_candidate_requests.jsonl", layer["requests"])
    write_jsonl(proof_dir / "rollback_plans.jsonl", layer["rollback_plans"])
    write_json(proof_dir / "patch_hygiene_replay_record.json", layer["replay"])
