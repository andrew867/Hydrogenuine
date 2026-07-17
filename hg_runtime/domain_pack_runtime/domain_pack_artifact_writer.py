"""Write P28-1 domain pack builder artifacts."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_p28_1_artifacts(proof_dir: Path, layer: dict) -> None:
    write_json(proof_dir / "domain_pack_policy.json", layer["policy"])
    write_json(proof_dir / "p27_skill_graph_manifest.json", layer["p27_manifest"])
    write_jsonl(proof_dir / "domain_packs.jsonl", layer["domain_packs"])
    write_jsonl(proof_dir / "domain_pack_skill_links.jsonl", layer["domain_pack_skill_links"])
    write_jsonl(proof_dir / "domain_pack_boundaries.jsonl", layer["domain_pack_boundaries"])
    write_json(proof_dir / "domain_capability_map.json", layer["capability_map"])
    write_json(proof_dir / "domain_pack_builder_manifest.json", layer["builder_manifest"])
    write_json(proof_dir / "replay_result.json", {"replay_deterministic": layer["replay_deterministic"]})
    write_jsonl(
        proof_dir / "receipt_chain.jsonl",
        layer["domain_packs"] + layer["domain_pack_skill_links"] + layer["domain_pack_boundaries"],
    )
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": layer["secret_redaction_passed"]})

