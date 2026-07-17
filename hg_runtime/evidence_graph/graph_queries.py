"""Evidence Graph queries — read-only graph inspection functions.

These functions never mutate the graph. They provide structural queries
for operator review. Edges are NOT proof. Citation is NOT truth.
"""

from __future__ import annotations


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
        if e.get("source_id") == node_id
    ]


def get_edges_to(graph: dict, node_id: str) -> list:
    """Get all edges pointing to the given node_id."""
    return [
        dict(e)
        for e in graph.get("edges", [])
        if e.get("target_id") == node_id
    ]


def find_unsupported_claims(graph: dict) -> list:
    """Return claim nodes with no inbound 'claim_supported_by_source_candidate' edges.

    A claim is considered unsupported if no edge of type
    'claim_supported_by_source_candidate' points to it.
    """
    claim_nodes = [
        n for n in graph.get("nodes", [])
        if n.get("node_type") == "claim"
    ]

    supported_node_ids = set()
    for edge in graph.get("edges", []):
        if edge.get("edge_type") == "claim_supported_by_source_candidate":
            supported_node_ids.add(edge.get("target_id"))

    return [
        dict(c) for c in claim_nodes
        if c.get("node_id") not in supported_node_ids
    ]


def find_evidence_gaps(graph: dict) -> list:
    """Return all evidence_gap nodes."""
    return [
        dict(n) for n in graph.get("nodes", [])
        if n.get("node_type") == "evidence_gap"
    ]


def find_contradictions(graph: dict) -> list:
    """Return all contradiction nodes."""
    return [
        dict(n) for n in graph.get("nodes", [])
        if n.get("node_type") == "contradiction"
    ]


def find_promotion_decisions(graph: dict) -> list:
    """Return all promotion_decision nodes."""
    return [
        dict(n) for n in graph.get("nodes", [])
        if n.get("node_type") == "promotion_decision"
    ]


def graph_summary(graph: dict) -> dict:
    """Summary statistics for the graph.

    Returns node_count_by_type, edge_count_by_type,
    unsupported_claims_count, evidence_gap_count, contradiction_count.
    """
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
    evidence_gaps = find_evidence_gaps(graph)
    contradictions = find_contradictions(graph)

    return {
        "node_count_by_type": node_counts,
        "edge_count_by_type": edge_counts,
        "unsupported_claims_count": len(unsupported),
        "evidence_gap_count": len(evidence_gaps),
        "contradiction_count": len(contradictions),
    }
