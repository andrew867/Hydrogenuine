"""
Viz Phase 6: Advanced — timeline playback, causal graph, export, WCAG a11y (read-only).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.viz.adapters.ledger_stream_adapter import adapt_ledger_stream
from hg_core.viz.adapters.impact_adapter import adapt_impact_graph
from hg_core.viz.adapters.materializer_adapter import adapt_materializer_graph
from hg_core.viz.adapters.systems_adapter import adapt_data_map
from hg_core.viz.adapters.trust_policy_adapter import adapt_trust_bands


def adapt_timeline_playback(
    workspace_root: Path,
    limit: int = 200,
    scope_type: Optional[str] = None,
    scope_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return chronological timeline for playback: items with ts, and min_ts/max_ts for slider bounds.
    Read-only; uses ledger stream.
    """
    root = Path(workspace_root)
    stream = adapt_ledger_stream(root, limit=limit, scope_type=scope_type, scope_id=scope_id)
    items = stream.get("items") or []
    ts_values = [it.get("ts") for it in items if it.get("ts")]
    return {
        "items": items,
        "min_ts": min(ts_values) if ts_values else "",
        "max_ts": max(ts_values) if ts_values else "",
        "has_more": stream.get("has_more", False),
    }


def adapt_causal_graph(
    workspace_root: Path,
    limit: int = 500,
) -> Dict[str, Any]:
    """
    Return causal/dependency graph: impact graph with DERIVES_FROM, DEPENDS_ON and similar edges.
    Read-only; same schema as impact graph (nodes, edges with evidence_refs).
    """
    return adapt_impact_graph(Path(workspace_root), limit=limit)


def adapt_viz_export(
    workspace_root: Path,
    export_type: str = "graph",
    limit: int = 500,
) -> Dict[str, Any]:
    """
    Return serializable viz snapshot for export. export_type: graph | timeline | full.
    graph: main materialized graph; timeline: playback timeline; full: graph + timeline + data_map + trust_bands.
    """
    root = Path(workspace_root)
    export_type = (export_type or "graph").strip().lower()
    out: Dict[str, Any] = {"export_type": export_type, "limit": limit}

    if export_type == "graph":
        out["graph"] = adapt_materializer_graph(root, limit=limit)
    elif export_type == "timeline":
        out["timeline"] = adapt_timeline_playback(root, limit=limit)
    elif export_type == "full":
        out["graph"] = adapt_materializer_graph(root, limit=limit)
        out["timeline"] = adapt_timeline_playback(root, limit=limit)
        out["data_map"] = adapt_data_map(root)
        out["trust_bands"] = adapt_trust_bands(root)
    else:
        out["graph"] = adapt_materializer_graph(root, limit=limit)
    return out


def adapt_a11y_metadata() -> Dict[str, Any]:
    """
    Return WCAG-oriented accessibility metadata for viz: suggested ARIA roles, label patterns,
    live region summary template. Use from frontend to apply aria-* attributes.
    """
    return {
        "node_role": "listitem",
        "graph_role": "graph",
        "edge_role": "presentation",
        "timeline_role": "region",
        "timeline_aria_label": "Event timeline",
        "graph_aria_label": "Relationship graph",
        "live_region_summary_template": "Graph has {node_count} nodes and {edge_count} edges.",
        "focus_order_hint": "Navigate nodes by tab; edges are decorative.",
    }
