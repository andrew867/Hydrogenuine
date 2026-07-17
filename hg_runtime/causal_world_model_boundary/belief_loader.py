"""Load WMBR-03 belief revision ledger artifacts.

The belief revision ledger is an *input*. A belief state is not truth and a
belief revision is not certainty. Only provenance-bound belief states may seed
causal hypotheses.
"""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.causal_world_model_boundary.schemas import CausalBoundaryError


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def discover_latest_bundle(proof_root: Path) -> Path | None:
    """Return the newest WMBR-03 proof bundle directory, or None."""
    proof_root = Path(proof_root)
    candidates = sorted(p.parent for p in proof_root.glob("*/belief_revision_manifest.json"))
    return candidates[-1] if candidates else None


def load_ledger_bundle(bundle_dir: Path) -> dict:
    """Load a WMBR-03 proof bundle into the in-memory shape used downstream."""
    bundle_dir = Path(bundle_dir)
    manifest_path = bundle_dir / "belief_revision_manifest.json"
    if not manifest_path.exists():
        raise CausalBoundaryError("input_belief_revision_ledger_required")
    summary_path = bundle_dir / "gate_result.json"
    return {
        "source_bundle": str(bundle_dir),
        "belief_states": _load_jsonl(bundle_dir / "belief_states.jsonl"),
        "belief_revisions": _load_jsonl(bundle_dir / "belief_revisions.jsonl"),
        "evidence_receipts": _load_jsonl(bundle_dir / "evidence_receipts.jsonl"),
        "contradiction_records": _load_jsonl(bundle_dir / "contradiction_records.jsonl"),
        "retraction_records": _load_jsonl(bundle_dir / "retraction_records.jsonl"),
        "provenance_chains": _load_jsonl(bundle_dir / "provenance_chains.jsonl"),
        "manifest": _load_json(manifest_path),
        "summary": _load_json(summary_path) if summary_path.exists() else {},
    }


def validate_ledger_bundle(bundle: dict) -> None:
    """Refuse a bundle missing the required belief revision ledger inputs."""
    if not bundle:
        raise CausalBoundaryError("input_belief_revision_ledger_required")
    if not bundle.get("manifest"):
        raise CausalBoundaryError("input_belief_revision_ledger_required")
    if not bundle.get("belief_states"):
        raise CausalBoundaryError("belief_states_required")
    if bundle.get("evidence_receipts") is None:
        raise CausalBoundaryError("evidence_receipts_required")
