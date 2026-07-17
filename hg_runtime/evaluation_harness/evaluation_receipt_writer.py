"""P31 evaluation receipt writer — writes receipts and refusals to proof bundles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_runtime.local_evidence_bridge.artifact_writer import write_json, write_jsonl


def write_receipt_artifacts(
    proof_dir: Path,
    receipts: list[dict[str, Any]],
    refusals: list[dict[str, Any]],
    boundary_check: dict[str, Any],
) -> None:
    proof_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(proof_dir / "receipts.jsonl", receipts)
    write_jsonl(proof_dir / "refusals.jsonl", refusals)
    write_json(proof_dir / "boundary_check.json", boundary_check)
    write_json(proof_dir / "refusal_coverage.json", {
        "refusal_count": len(refusals),
        "receipt_count": len(receipts),
        "claim_types_covered": sorted({r["claim_type"] for r in refusals}),
    })
