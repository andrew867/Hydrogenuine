"""P26 recall artifact writers."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_p26_2_bundle(layer: dict, proof_dir: Path, summary: dict) -> None:
    write_json(proof_dir / "gate_result.json", summary)
    write_jsonl(proof_dir / "recall_queries.jsonl", layer["queries"])
    write_jsonl(proof_dir / "recall_results.jsonl", layer["results"])
    write_json(proof_dir / "recall_index.json", layer["recall_index"]["index"])
    write_json(proof_dir / "recall_manifest.json", layer["manifest"])
    write_json(proof_dir / "replay_result.json", layer["replay"])
    write_jsonl(proof_dir / "receipt_chain.jsonl", layer["queries"] + layer["results"])
    write_json(proof_dir / "redaction_audit.json", {"secret_redaction_passed": summary["secret_redaction_passed"]})

