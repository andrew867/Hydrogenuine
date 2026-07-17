"""
Metacognition dashboard API: list self-assessments, calibration metrics, tool reliability.
Reads from materialized views (run metacognition materializer first).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _materialized_root(workspace_root: Path) -> Path:
    return Path(workspace_root) / "memory" / "materialized"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def list_self_assessments(
    workspace_root: Path,
    *,
    decision_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List self-assessments from materialized index, optionally filtered by decision_id."""
    workspace_root = Path(workspace_root)
    rows = _load_jsonl(_materialized_root(workspace_root) / "self_assessments.jsonl")
    if decision_id is not None:
        rows = [r for r in rows if r.get("decision_id") == decision_id]
    return rows[offset : offset + limit]


def get_calibration_metrics(workspace_root: Path) -> Dict[str, Any]:
    """Return calibration timeseries and bucketed curve from materialized views."""
    workspace_root = Path(workspace_root)
    root = _materialized_root(workspace_root)
    timeseries = _load_jsonl(root / "calibration_timeseries.jsonl")
    curve = _load_jsonl(root / "calibration_curve.jsonl")
    mean_brier = 0.0
    if timeseries:
        mean_brier = sum(t.get("brier_score", 0) for t in timeseries) / len(timeseries)
    return {
        "calibration_timeseries": timeseries,
        "calibration_curve": curve,
        "mean_brier_score": mean_brier,
        "n_predictions_evaluated": len(timeseries),
    }


def get_tool_reliability(workspace_root: Path, tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return tool reliability stats (success rate, avg latency, counts) from materialized index."""
    workspace_root = Path(workspace_root)
    rows = _load_jsonl(_materialized_root(workspace_root) / "tool_reliability.jsonl")
    if tool_name is not None:
        rows = [r for r in rows if r.get("tool_name") == tool_name]
    return rows


def check_has_self_assessment(workspace_root: Path, decision_id: str) -> bool:
    """
    Return True if at least one SELF_ASSESSMENT_RECORDED exists for the given decision_id.
    Gating middleware can use this to enforce mandatory assessment before commit (policy-driven).
    """
    workspace_root = Path(workspace_root)
    rows = _load_jsonl(_materialized_root(workspace_root) / "self_assessments.jsonl")
    return any(r.get("decision_id") == decision_id for r in rows)
