"""Artifact writer for DTX-3 packet evaluation."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_dtx_packet_artifacts(*, proof_dir: Path, layer: dict, replay_result: dict, redaction_audit: dict) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_json(proof_dir / "dtx_packet_evaluation_manifest.json", layer["dtx_packet_evaluation_manifest"])
    write_jsonl(proof_dir / "dtx_claim_packets.jsonl", layer["dtx_claim_packets"])
    write_jsonl(proof_dir / "dtx_second_source_results.jsonl", layer["dtx_second_source_results"])
    write_jsonl(proof_dir / "dtx_contradiction_packets.jsonl", layer["dtx_contradiction_packets"])
    write_json(proof_dir / "dtx_operator_dashboard.json", layer["dtx_operator_dashboard"])
    (proof_dir / "dtx_operator_dashboard.md").write_text(layer["dtx_operator_dashboard_md"], encoding="utf-8")
    write_json(proof_dir / "replay_result.json", replay_result)
    write_jsonl(
        proof_dir / "receipt_chain.jsonl",
        layer["dtx_claim_packets"] + layer["dtx_second_source_results"] + layer["dtx_contradiction_packets"],
    )
    write_json(proof_dir / "redaction_audit.json", redaction_audit)
