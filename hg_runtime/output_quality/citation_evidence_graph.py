"""Citation/Evidence Graph — directed graph tracking citation relationships
between claims, sources, and evidence.

Edges are NOT proof. Citation existence is NOT truth. The graph is a
structural aid for operator review, not an authority mechanism.

Promotion is NEVER allowed. Operator review is ALWAYS required.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

SCHEMA_VERSION = "citation_evidence_graph_v1"

NODE_TYPES = {"claim", "source", "evidence", "seed", "model_output"}

EDGE_TYPES = {"cites", "supports", "contradicts", "derived_from", "extracted_from"}

_INVARIANTS = {
    "citation_existence_is_not_truth": True,
    "evidence_graph_edge_is_not_proof": True,
    "promotion_allowed": False,
    "operator_review_required": True,
    "model_output_treated_as_truth": False,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_graph() -> dict:
    """Create an empty citation evidence graph."""
    return {
        "schema": SCHEMA_VERSION,
        "nodes": [],
        "edges": [],
        **copy.deepcopy(_INVARIANTS),
        "created_at": _utc_now_iso(),
    }


def add_node(
    graph: dict,
    *,
    node_id: str,
    node_type: str,
    label: str,
    metadata: dict | None = None,
) -> dict:
    """Add a node to the graph. Returns new graph.

    node_type must be one of: claim, source, evidence, seed, model_output.
    """
    if node_type not in NODE_TYPES:
        raise ValueError(
            f"Invalid node_type '{node_type}'. Must be one of: {sorted(NODE_TYPES)}"
        )

    node = {
        "node_id": node_id,
        "node_type": node_type,
        "label": label,
        "metadata": metadata or {},
        "added_at": _utc_now_iso(),
    }

    graph = dict(graph)
    graph["nodes"] = list(graph.get("nodes", [])) + [node]

    # Re-enforce invariants
    graph.update(copy.deepcopy(_INVARIANTS))

    return graph


def add_edge(
    graph: dict,
    *,
    source_node_id: str,
    target_node_id: str,
    edge_type: str,
    weight: float = 1.0,
    metadata: dict | None = None,
    stop_panic: bool = False,
) -> dict:
    """Add an edge to the graph. Returns new graph.

    edge_type must be one of: cites, supports, contradicts, derived_from,
    extracted_from.

    Edge weight is advisory, not authority.

    If stop_panic is True, returns the graph unchanged (STOP/PANIC block).
    """
    if stop_panic:
        return graph

    if edge_type not in EDGE_TYPES:
        raise ValueError(
            f"Invalid edge_type '{edge_type}'. Must be one of: {sorted(EDGE_TYPES)}"
        )

    edge = {
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
        "edge_type": edge_type,
        "weight": weight,
        "weight_is_advisory_not_authority": True,
        "metadata": metadata or {},
        "added_at": _utc_now_iso(),
    }

    graph = dict(graph)
    graph["edges"] = list(graph.get("edges", [])) + [edge]

    # Re-enforce invariants
    graph.update(copy.deepcopy(_INVARIANTS))

    return graph


def get_node(graph: dict, node_id: str) -> dict | None:
    """Get a node by node_id. Returns None if not found."""
    for node in graph.get("nodes", []):
        if node.get("node_id") == node_id:
            return dict(node)
    return None


def get_edges_from(graph: dict, node_id: str) -> list:
    """Get all edges originating from the given node_id."""
    return [
        dict(e)
        for e in graph.get("edges", [])
        if e.get("source_node_id") == node_id
    ]


def get_edges_to(graph: dict, node_id: str) -> list:
    """Get all edges pointing to the given node_id."""
    return [
        dict(e)
        for e in graph.get("edges", [])
        if e.get("target_node_id") == node_id
    ]


def find_contradictions(graph: dict) -> list:
    """Return all edges of type 'contradicts'."""
    return [
        dict(e)
        for e in graph.get("edges", [])
        if e.get("edge_type") == "contradicts"
    ]


def find_unsupported_claims(graph: dict) -> list:
    """Return claim nodes with no inbound 'supports' or 'cites' edges.

    A claim is considered unsupported if no edge of type 'supports' or
    'cites' points to it.
    """
    claim_nodes = [
        n for n in graph.get("nodes", [])
        if n.get("node_type") == "claim"
    ]

    supported_node_ids = set()
    for edge in graph.get("edges", []):
        if edge.get("edge_type") in ("supports", "cites"):
            supported_node_ids.add(edge.get("target_node_id"))

    return [
        dict(c) for c in claim_nodes
        if c.get("node_id") not in supported_node_ids
    ]


def graph_summary(graph: dict) -> dict:
    """Summary statistics for the graph."""
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    node_counts = {}
    for n in nodes:
        nt = n.get("node_type", "unknown")
        node_counts[nt] = node_counts.get(nt, 0) + 1

    edge_counts = {}
    for e in edges:
        et = e.get("edge_type", "unknown")
        edge_counts[et] = edge_counts.get(et, 0) + 1

    unsupported = find_unsupported_claims(graph)
    contradictions = find_contradictions(graph)

    return {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "node_counts_by_type": node_counts,
        "edge_counts_by_type": edge_counts,
        "unsupported_claims_count": len(unsupported),
        "contradiction_count": len(contradictions),
        "citation_existence_is_not_truth": True,
        "evidence_graph_edge_is_not_proof": True,
        "promotion_allowed": False,
        "operator_review_required": True,
    }


def validate_graph(graph: dict) -> list[str]:
    """Validate graph invariants. Returns list of errors (empty = valid)."""
    errors = []

    if graph.get("schema") != SCHEMA_VERSION:
        errors.append(
            f"wrong schema: expected {SCHEMA_VERSION}, got {graph.get('schema')}"
        )

    # Core invariants — must ALWAYS hold
    if graph.get("citation_existence_is_not_truth") is not True:
        errors.append("citation_existence_is_not_truth must be True")

    if graph.get("evidence_graph_edge_is_not_proof") is not True:
        errors.append("evidence_graph_edge_is_not_proof must be True")

    if graph.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")

    if graph.get("operator_review_required") is not True:
        errors.append("operator_review_required must be True")

    if graph.get("model_output_treated_as_truth") is not False:
        errors.append("model_output_treated_as_truth must be False")

    # Validate node types
    for i, node in enumerate(graph.get("nodes", [])):
        if node.get("node_type") not in NODE_TYPES:
            errors.append(
                f"node[{i}] has invalid node_type: {node.get('node_type')}"
            )

    # Validate edge types
    for i, edge in enumerate(graph.get("edges", [])):
        if edge.get("edge_type") not in EDGE_TYPES:
            errors.append(
                f"edge[{i}] has invalid edge_type: {edge.get('edge_type')}"
            )

    return errors
