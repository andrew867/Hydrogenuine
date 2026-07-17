"""
Delegation quality checks and scoring (Autonomy Ch5 Phase 2).

Per docs/specs/delegation_quality_checks.md: must-level checks, quality score,
runs below threshold marked degraded and blocked from external writes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

DEFAULT_QUALITY_THRESHOLD = 0.6  # score in [0, 1]; below = degraded


def delegation_quality_score(
    metrics: Dict[str, Any],
    nodes: Optional[List[Dict[str, Any]]] = None,
    edges: Optional[List[Dict[str, Any]]] = None,
) -> float:
    """
    Compute delegation quality score in [0, 1]. Penalize missing criteria, missing owners,
    misaligned handoffs, excessive depth/width. nodes/edges optional for finer scoring.
    """
    score = 1.0
    depth = metrics.get("delegation_depth_max", 0)
    width = metrics.get("delegation_width_max", 0)
    total = metrics.get("total_work_items", 0)
    handoffs = metrics.get("handoff_count", 0)
    if depth > 10:
        score -= 0.2
    if width > 20:
        score -= 0.15
    if total > 50:
        score -= 0.1
    if edges:
        aligned = sum(1 for e in edges if e.get("receipt_aligned", True))
        total_edges = len(edges)
        if total_edges > 0 and aligned < total_edges:
            score -= 0.2 * (1 - aligned / total_edges)
    if nodes:
        with_owner = sum(1 for n in nodes if n.get("owner"))
        if nodes and with_owner < len(nodes):
            score -= 0.2 * (1 - with_owner / len(nodes))
    return max(0.0, min(1.0, score))


def is_run_degraded(
    quality_score: float,
    threshold: float = DEFAULT_QUALITY_THRESHOLD,
) -> bool:
    """True if run is below quality threshold and should not execute external writes."""
    return quality_score < threshold


def check_quality(
    metrics: Dict[str, Any],
    nodes: Optional[List[Dict[str, Any]]] = None,
    edges: Optional[List[Dict[str, Any]]] = None,
    threshold: float = DEFAULT_QUALITY_THRESHOLD,
) -> Dict[str, Any]:
    """Return { score, degraded, threshold }."""
    score = delegation_quality_score(metrics, nodes=nodes, edges=edges)
    degraded = is_run_degraded(score, threshold)
    return {"score": score, "degraded": degraded, "threshold": threshold}
