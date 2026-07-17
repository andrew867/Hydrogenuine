"""
Viz Phase 2: Adapter from impact graph to unified viz schema (read-only).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_core.impact.build_graph import build_impact_graph
from hg_core.viz.schema import normalize_evidence_refs, viz_node, viz_edge


def adapt_impact_graph(
    workspace_root: Path,
    types: Optional[List[str]] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """Build impact graph and return unified viz schema: nodes and edges with evidence_refs."""
    root = Path(workspace_root)
    nodes_by_id, edges_tuples = build_impact_graph(root)
    node_ids_in_scope = set()
    nodes_out: List[Dict[str, Any]] = []
    for nid, attrs in nodes_by_id.items():
        if len(nodes_out) >= limit:
            break
        node_type = attrs.get("type", "unknown")
        if types and node_type not in types:
            continue
        node_ids_in_scope.add(nid)
        ev_refs = normalize_evidence_refs(attrs.get("evidence_refs") or [])
        nodes_out.append(
            viz_node(
                nid,
                node_type,
                {k: v for k, v in attrs.items() if k not in ("type", "evidence_refs")},
                ev_refs,
            )
        )
    edges_out: List[Dict[str, Any]] = []
    for fr, to, etyp, ev_refs_raw in edges_tuples:
        if fr in node_ids_in_scope and to in node_ids_in_scope:
            ev_refs = normalize_evidence_refs(ev_refs_raw)
            edges_out.append(viz_edge(fr, to, etyp, ev_refs))
    return {"nodes": nodes_out, "edges": edges_out}
