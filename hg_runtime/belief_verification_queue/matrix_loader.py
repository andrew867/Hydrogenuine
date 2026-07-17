"""Load WMBR-01A Cross-Model Perspective Matrix artifacts.

Matrix artifacts are an *input* to the verification queue. They are spectroscopy
records of what models said, never beliefs and never evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.belief_verification_queue.schemas import BeliefVerificationQueueError

WMBR_01A_PROOF_GLOB = "docs/proofs/autonomous_agent_zero/WMBR-01A-CROSS-MODEL-PERSPECTIVE"

REQUIRED_FILES = (
    "perspective_matrix.json",
    "divergence_matrix.json",
)


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
    """Return the newest WMBR-01A proof bundle directory, or None."""
    proof_root = Path(proof_root)
    candidates = sorted(p.parent for p in proof_root.glob("*/perspective_matrix.json"))
    return candidates[-1] if candidates else None


def load_matrix_bundle(bundle_dir: Path) -> dict:
    """Load a WMBR-01A proof bundle into the in-memory shape used downstream."""
    bundle_dir = Path(bundle_dir)
    for required in REQUIRED_FILES:
        if not (bundle_dir / required).exists():
            if required == "perspective_matrix.json":
                raise BeliefVerificationQueueError("perspective_matrix_required")
            raise BeliefVerificationQueueError("divergence_matrix_required")
    summary_path = bundle_dir / "cross_model_perspective_summary.json"
    bundle = {
        "source_bundle": str(bundle_dir),
        "perspective_matrix": _load_json(bundle_dir / "perspective_matrix.json"),
        "divergence_matrix": _load_json(bundle_dir / "divergence_matrix.json"),
        "omission_patterns": _load_jsonl(bundle_dir / "omission_patterns.jsonl"),
        "refusal_patterns": _load_jsonl(bundle_dir / "refusal_patterns.jsonl"),
        "framing_signatures": _load_jsonl(bundle_dir / "framing_signatures.jsonl"),
        "moral_conflict_records": _load_jsonl(bundle_dir / "moral_conflict_records.jsonl"),
        "evidence_gap_tasks": _load_jsonl(bundle_dir / "evidence_gap_tasks.jsonl"),
        "summary": _load_json(summary_path) if summary_path.exists() else {},
    }
    return bundle


def validate_matrix_bundle(bundle: dict) -> None:
    """Refuse a bundle that is missing required matrix inputs."""
    if not bundle:
        raise BeliefVerificationQueueError("input_matrix_required")
    pm = bundle.get("perspective_matrix")
    if not pm or not pm.get("cells"):
        raise BeliefVerificationQueueError("perspective_matrix_required")
    if not bundle.get("divergence_matrix"):
        raise BeliefVerificationQueueError("divergence_matrix_required")
    if bundle.get("evidence_gap_tasks") is None:
        raise BeliefVerificationQueueError("evidence_gap_tasks_required")
