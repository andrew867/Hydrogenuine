"""Artifact writer for EWP-4 operator dashboard."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_dashboard_artifacts(
    *,
    proof_dir: Path,
    dashboard: dict,
    dashboard_md: str,
    review_statuses: list[dict],
    manifest: dict,
    replay_result: dict,
    redaction_audit: dict,
) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "operator_packet_dashboard.json", dashboard)
    (proof_dir / "operator_packet_dashboard.md").write_text(dashboard_md, encoding="utf-8")
    write_jsonl(proof_dir / "packet_review_status.jsonl", review_statuses)
    write_json(proof_dir / "dashboard_manifest.json", manifest)
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(proof_dir / "receipt_chain.jsonl", [dashboard] + review_statuses)
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
