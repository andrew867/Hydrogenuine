"""
Viz Phase 1–6: Read-only viz API (graph, evidence_refs, DAG, ledger stream, delegation, impact,
trust/policy views, explainers, data map, widgets, deep-linking, timeline, causal, export, a11y).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.viz.adapters.materializer_adapter import adapt_materializer_graph
from hg_core.viz.adapters.ledger_adapter import adapt_ledger_events_to_nodes
from hg_core.viz.adapters.impact_adapter import adapt_impact_graph
from hg_core.viz.adapters.ledger_stream_adapter import adapt_ledger_stream
from hg_core.viz.adapters.delegation_adapter import adapt_delegation_graph
from hg_core.viz.adapters.dag_adapter import adapt_dag_view
from hg_core.viz.adapters.trust_policy_adapter import (
    adapt_trust_bands,
    adapt_budget_view,
    adapt_escrow_view,
    adapt_gating_view,
)
from hg_core.viz.adapters.explainer_adapter import (
    adapt_decision_explainer,
    adapt_compare_decisions,
    adapt_proof_path,
)
from hg_core.viz.adapters.systems_adapter import (
    adapt_data_map,
    adapt_operator_widgets,
    adapt_deep_link,
)
from hg_core.viz.adapters.advanced_adapter import (
    adapt_timeline_playback,
    adapt_causal_graph,
    adapt_viz_export,
    adapt_a11y_metadata,
)


def get_viz_graph(
    workspace_root: Path,
    types: Optional[List[str]] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """Read-only: return graph { nodes, edges } in unified schema with evidence_refs."""
    return adapt_materializer_graph(Path(workspace_root), types=types, limit=limit)


def get_viz_evidence_refs(
    workspace_root: Path,
    node_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Read-only: evidence_refs for a node (from graph) or from ledger event nodes if node_id is None."""
    root = Path(workspace_root)
    if node_id is not None:
        from hg_core.graph_mirror import build_graph
        from hg_core.viz.schema import normalize_evidence_refs
        nodes_by_id, edges = build_graph(root)
        if node_id in nodes_by_id:
            return normalize_evidence_refs(nodes_by_id[node_id].get("evidence_refs") or [])
        for fr, to, _et, ev_refs in edges:
            if fr == node_id or to == node_id:
                return normalize_evidence_refs(ev_refs or [])
        return []
    nodes = adapt_ledger_events_to_nodes(root, limit=200)
    out: List[Dict[str, Any]] = []
    for n in nodes:
        out.extend(n.get("evidence_refs") or [])
    return out


# --- Phase 2: Graph and relationship views ---


def get_viz_impact_graph(
    workspace_root: Path,
    types: Optional[List[str]] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """Read-only: impact graph (nodes, edges) in unified schema with evidence_refs."""
    return adapt_impact_graph(Path(workspace_root), types=types, limit=limit)


def get_viz_ledger_stream(
    workspace_root: Path,
    limit: int = 100,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Read-only: ledger events as chronological stream { items, has_more }."""
    return adapt_ledger_stream(
        Path(workspace_root),
        limit=limit,
        scope_type=scope_type,
        scope_id=scope_id,
    )


def get_viz_delegation_graph(
    workspace_root: Path,
    limit: int = 200,
) -> Dict[str, Any]:
    """Read-only: delegation view (handoff and work_item nodes and edges)."""
    return adapt_delegation_graph(Path(workspace_root), limit=limit)


def get_viz_dag(
    workspace_root: Path,
    run_id: Optional[str] = None,
    runs_limit: int = 50,
) -> Dict[str, Any]:
    """Read-only: DAG view — list of runs and optionally graph for one run."""
    return adapt_dag_view(Path(workspace_root), run_id=run_id, runs_limit=runs_limit)


# --- Phase 3: Trust and policy views ---


def get_viz_trust_bands(workspace_root: Path) -> List[Dict[str, Any]]:
    """Read-only: trust bands from stakes policy (band_index, name, max_action)."""
    return adapt_trust_bands(Path(workspace_root))


def get_viz_budget_view(workspace_root: Path) -> Dict[str, Any]:
    """Read-only: budget view (policy_budget, operator_budgets)."""
    return adapt_budget_view(Path(workspace_root))


def get_viz_escrow_view(workspace_root: Path) -> Dict[str, Any]:
    """Read-only: escrow view (lock_amount_default, high_impact_actions)."""
    return adapt_escrow_view(Path(workspace_root))


def get_viz_gating_view(workspace_root: Path) -> Dict[str, Any]:
    """Read-only: gating view (trust_band_limits, require_approval_for_actions, high_impact_actions)."""
    return adapt_gating_view(Path(workspace_root))


# --- Phase 4: Explorable explainers ---


def get_viz_decision_explainer(workspace_root: Path, decision_id: str) -> Dict[str, Any]:
    """Read-only: decision explainer (claims, value_weights, context_ref, produced_artifact_ids, title, event_id)."""
    return adapt_decision_explainer(Path(workspace_root), decision_id)


def get_viz_compare_decisions(
    workspace_root: Path,
    decision_id_a: str,
    decision_id_b: str,
) -> Dict[str, Any]:
    """Read-only: compare two decisions (overlapping_claim_ids, value_weight_diffs, same_facts_different_action)."""
    return adapt_compare_decisions(Path(workspace_root), decision_id_a, decision_id_b)


def get_viz_proof_path(workspace_root: Path, decision_id: str) -> Dict[str, Any]:
    """Read-only: proof path for a decision (decision, predictions, evaluations, self_assessments, representation_inspection_result)."""
    return adapt_proof_path(Path(workspace_root), decision_id)


def get_viz_repr_interp_results(
    workspace_root: Path,
    run_dir: Optional[Path] = None,
    run_id: Optional[str] = None,
    decision_id: Optional[str] = None,
    node_id: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Read-only: representation interpretability inspection results (Layer 8 Phase 4 wiring)."""
    try:
        from hg_core.repr_interp.api import api_repr_interp_results
        return api_repr_interp_results(
            Path(workspace_root),
            run_dir=run_dir,
            run_id=run_id,
            decision_id=decision_id,
            node_id=node_id,
            limit=limit,
        )
    except ImportError:
        return {"results": []}


# --- Phase 5: System-of-systems and dashboards ---


def get_viz_data_map(workspace_root: Path) -> Dict[str, Any]:
    """Read-only: data map (ledger scopes, materialized tables, DAG runs) for system-of-systems view."""
    return adapt_data_map(Path(workspace_root))


def get_viz_operator_widgets(
    workspace_root: Path,
    role: str = "operator",
    investor_mode: bool = False,
) -> Dict[str, Any]:
    """Read-only: operator (or role) dashboard widgets with deep-link hints."""
    return adapt_operator_widgets(Path(workspace_root), role=role, investor_mode=investor_mode)


def get_viz_deep_link(
    workspace_root: Path,
    target_type: str,
    target_id: str,
) -> Dict[str, Any]:
    """Read-only: deep-link descriptor (view, params, fragment) for a target."""
    return adapt_deep_link(Path(workspace_root), target_type, target_id)


# --- Phase 6: Advanced (timeline playback, causal graph, export, a11y) ---


def get_viz_timeline_playback(
    workspace_root: Path,
    limit: int = 200,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Read-only: timeline for playback (items, min_ts, max_ts, has_more)."""
    return adapt_timeline_playback(
        Path(workspace_root),
        limit=limit,
        scope_type=scope_type,
        scope_id=scope_id,
    )


def get_viz_causal_graph(
    workspace_root: Path,
    limit: int = 500,
) -> Dict[str, Any]:
    """Read-only: causal/dependency graph (nodes, edges with evidence_refs)."""
    return adapt_causal_graph(Path(workspace_root), limit=limit)


def get_viz_export(
    workspace_root: Path,
    export_type: str = "graph",
    limit: int = 500,
) -> Dict[str, Any]:
    """Read-only: serializable viz snapshot for export (graph | timeline | full)."""
    return adapt_viz_export(Path(workspace_root), export_type=export_type, limit=limit)


def get_viz_a11y_metadata() -> Dict[str, Any]:
    """Read-only: WCAG a11y metadata (ARIA roles, label patterns, live region template)."""
    return adapt_a11y_metadata()
