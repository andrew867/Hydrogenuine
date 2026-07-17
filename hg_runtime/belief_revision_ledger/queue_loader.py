"""Load WMBR-02 belief-conflict / verification-queue artifacts.

Queue artifacts are an *input* to belief revision. A queued verification task is
not evidence and a candidate claim is not a belief.
"""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.belief_revision_ledger.schemas import BeliefRevisionError


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
    """Return the newest WMBR-02 proof bundle directory, or None."""
    proof_root = Path(proof_root)
    candidates = sorted(p.parent for p in proof_root.glob("*/verification_queue_manifest.json"))
    return candidates[-1] if candidates else None


def load_queue_bundle(bundle_dir: Path) -> dict:
    """Load a WMBR-02 proof bundle into the in-memory shape used downstream."""
    bundle_dir = Path(bundle_dir)
    manifest_path = bundle_dir / "verification_queue_manifest.json"
    if not manifest_path.exists():
        raise BeliefRevisionError("input_queue_required")
    summary_path = bundle_dir / "gate_result.json"
    return {
        "source_bundle": str(bundle_dir),
        "candidate_claims": _load_jsonl(bundle_dir / "candidate_claims.jsonl"),
        "verification_tasks": _load_jsonl(bundle_dir / "verification_tasks.jsonl"),
        "belief_conflicts": _load_jsonl(bundle_dir / "belief_conflicts.jsonl"),
        "evidence_policy_receipts": _load_jsonl(bundle_dir / "evidence_policy_receipts.jsonl"),
        "queue_manifest": _load_json(manifest_path),
        "summary": _load_json(summary_path) if summary_path.exists() else {},
    }


def validate_queue_bundle(bundle: dict) -> None:
    """Refuse a bundle missing the required queue inputs."""
    if not bundle:
        raise BeliefRevisionError("input_queue_required")
    if not bundle.get("queue_manifest"):
        raise BeliefRevisionError("input_queue_required")
    if not bundle.get("candidate_claims"):
        raise BeliefRevisionError("candidate_claims_required")
    if bundle.get("verification_tasks") is None:
        raise BeliefRevisionError("verification_tasks_required")
