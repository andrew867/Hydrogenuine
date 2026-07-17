"""Artifact writer for the SQP-5 review policy adapter."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_review_hint_artifacts(
    *,
    proof_dir: Path,
    hints: list[dict],
    priorities: list[dict],
    blocked_hints: list[dict],
    manifest: dict,
    replay_result: dict,
    redaction_audit: dict,
) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(proof_dir / "source_review_policy_hints.jsonl", hints)
    write_jsonl(proof_dir / "review_priority_records.jsonl", priorities)
    write_jsonl(proof_dir / "blocked_review_hint_records.jsonl", blocked_hints)
    write_json(proof_dir / "review_policy_adapter_manifest.json", manifest)
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", hints + priorities + blocked_hints)
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
