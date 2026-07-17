"""Load WMBR-04 causal world-model boundary artifacts.

The causal graph is an *input*. A causal hypothesis is not causal truth. Only
provisional (PROPOSED) hypotheses may emit active prediction candidates.
"""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.predictive_calibration.schemas import PredictiveCalibrationError


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
    """Return the newest WMBR-04 proof bundle directory, or None."""
    proof_root = Path(proof_root)
    candidates = sorted(p.parent for p in proof_root.glob("*/causal_graph_manifest.json"))
    return candidates[-1] if candidates else None


def load_causal_bundle(bundle_dir: Path) -> dict:
    """Load a WMBR-04 proof bundle into the in-memory shape used downstream."""
    bundle_dir = Path(bundle_dir)
    manifest_path = bundle_dir / "causal_graph_manifest.json"
    if not manifest_path.exists():
        raise PredictiveCalibrationError("input_causal_graph_required")
    summary_path = bundle_dir / "gate_result.json"
    return {
        "source_bundle": str(bundle_dir),
        "hypotheses": _load_jsonl(bundle_dir / "causal_hypotheses.jsonl"),
        "edges": _load_jsonl(bundle_dir / "causal_edges.jsonl"),
        "predictions": _load_jsonl(bundle_dir / "prediction_records.jsonl"),
        "manifest": _load_json(manifest_path),
        "summary": _load_json(summary_path) if summary_path.exists() else {},
    }


def validate_causal_bundle(bundle: dict) -> None:
    """Refuse a bundle missing the required causal graph inputs."""
    if not bundle:
        raise PredictiveCalibrationError("input_causal_graph_required")
    if not bundle.get("manifest"):
        raise PredictiveCalibrationError("input_causal_graph_required")
    if not bundle.get("hypotheses"):
        raise PredictiveCalibrationError("causal_hypotheses_required")
    if not bundle.get("edges"):
        raise PredictiveCalibrationError("causal_edges_required")
