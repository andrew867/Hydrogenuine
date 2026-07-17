"""
Autonomous delegation manager (Autonomy Ch5 Phase 3).

Thin manager: maintains graph state, enforces quality checks, applies budgets and detectors.
Blocks unsafe delegation patterns. Per docs/specs/autonomous_delegation_manager.md.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .delegation_graph import DelegationGraphBuilder, build_graph_from_events, persist_delegation_artifacts
from .delegation_quality import check_quality
from .intervention_policy import current_intervention, should_block_external_writes
from .emergent_behavior_detectors import run_default_detectors


def run_delegation_supervision(
    run_id: str,
    workflow_id: str,
    events: List[Dict[str, Any]],
    nodes_attempts: Optional[Dict[str, int]] = None,
    root_objective_summary: str = "",
    final_status: str = "success",
) -> Dict[str, Any]:
    """
    Build graph, run detectors, quality check, intervention. Return summary_dict shape
    with anomalies, quality, intervention, final_state (including external_writes_blocked).
    """
    graph_dict, summary_dict = build_graph_from_events(
        run_id, workflow_id, events, root_objective_summary=root_objective_summary
    )
    summary_dict["final_state"]["status"] = final_status
    metrics = summary_dict.get("metrics", {})
    anomalies = run_default_detectors(
        metrics, events=events, node_attempts=nodes_attempts or {}
    )
    summary_dict["anomalies"] = anomalies
    quality_result = check_quality(
        metrics, nodes=graph_dict.get("nodes"), edges=graph_dict.get("edges")
    )
    summary_dict["quality"] = quality_result
    intervention = current_intervention(
        {**metrics, "anomalies": anomalies}
    )
    summary_dict["intervention"] = intervention
    blocked = should_block_external_writes(
        intervention["step"], quality_result["degraded"]
    )
    summary_dict["final_state"]["external_writes_attempted"] = "no"
    summary_dict["final_state"]["external_writes_blocked"] = "yes" if blocked else "no"
    return summary_dict
