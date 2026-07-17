"""Load WMBR-05 predictive calibration artifacts.

The calibration layer is an *input*. A calibration record is not proof. Only
read-only consumption of prior artifacts is permitted.
"""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.world_model_audit.schemas import WorldModelAuditError


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
    """Return the newest WMBR-05 proof bundle directory, or None."""
    proof_root = Path(proof_root)
    candidates = sorted(p.parent for p in proof_root.glob("*/calibration_manifest.json"))
    return candidates[-1] if candidates else None


def load_calibration_bundle(bundle_dir: Path) -> dict:
    """Load a WMBR-05 proof bundle into the in-memory shape used downstream."""
    bundle_dir = Path(bundle_dir)
    manifest_path = bundle_dir / "calibration_manifest.json"
    if not manifest_path.exists():
        raise WorldModelAuditError("input_calibration_required")
    summary_path = bundle_dir / "gate_result.json"
    return {
        "source_bundle": str(bundle_dir),
        "prediction_candidates": _load_jsonl(bundle_dir / "prediction_candidates.jsonl"),
        "synthetic_outcomes": _load_jsonl(bundle_dir / "synthetic_outcome_receipts.jsonl"),
        "calibration_records": _load_jsonl(bundle_dir / "calibration_records.jsonl"),
        "uncertainty_scores": _load_jsonl(bundle_dir / "uncertainty_scores.jsonl"),
        "drift_records": _load_jsonl(bundle_dir / "prediction_drift_records.jsonl"),
        "hypotheses": _load_jsonl(bundle_dir / "causal_hypotheses_snapshot.jsonl"),
        "edges": _load_jsonl(bundle_dir / "causal_edges_snapshot.jsonl"),
        "manifest": _load_json(manifest_path),
        "summary": _load_json(summary_path) if summary_path.exists() else {},
    }


def validate_calibration_bundle(bundle: dict) -> None:
    """Refuse a bundle missing the required WMBR-05 inputs."""
    if not bundle:
        raise WorldModelAuditError("input_calibration_required")
    if not bundle.get("manifest"):
        raise WorldModelAuditError("input_calibration_required")
    if not bundle.get("prediction_candidates"):
        raise WorldModelAuditError("prediction_candidates_required")
    if not bundle.get("calibration_records"):
        raise WorldModelAuditError("calibration_records_required")


def load_retraction_records(bundle_dir: Path) -> list[dict]:
    """Load retraction records from a WMBR-03 proof bundle directory."""
    path = Path(bundle_dir) / "retraction_records.jsonl"
    return _load_jsonl(path)

