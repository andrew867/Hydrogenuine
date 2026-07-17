"""Evidence Graph builder — immutable graph construction functions.

Every mutation returns a new graph dict. Invariants are re-applied on
every operation to prevent drift.

Edges are NOT proof. Promotion is NEVER allowed.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone

from .graph_schema import (
    SCHEMA_VERSION,
    NODE_TYPES,
    EDGE_TYPES,
    _INVARIANTS,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_graph() -> dict:
    """Create an empty evidence graph with schema and invariants."""
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
    label: str = "",
    metadata: dict | None = None,
) -> dict:
    """Add a node to the graph. Returns new graph.

    node_type must be in NODE_TYPES. Raises ValueError if invalid.
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
    source_id: str,
    target_id: str,
    edge_type: str,
    weight: float = 1.0,
    metadata: dict | None = None,
    stop_panic: bool = False,
) -> dict:
    """Add an edge to the graph. Returns new graph.

    edge_type must be in EDGE_TYPES. Raises ValueError if invalid.

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
        "source_id": source_id,
        "target_id": target_id,
        "edge_type": edge_type,
        "weight": weight,
        "weight_is_advisory": True,
        "metadata": metadata or {},
        "added_at": _utc_now_iso(),
    }

    graph = dict(graph)
    graph["edges"] = list(graph.get("edges", [])) + [edge]

    # Re-enforce invariants
    graph.update(copy.deepcopy(_INVARIANTS))

    return graph


def build_seed_claim_chain(
    graph: dict,
    *,
    seed_id: str,
    seed_label: str,
    claim_id: str,
    claim_label: str,
    evidence_gap_id: str | None = None,
    falsification_target_id: str | None = None,
) -> dict:
    """Convenience: build a seed -> claim chain with optional evidence_gap
    and falsification_target nodes.

    Returns new graph with all nodes and edges added.
    """
    # Add seed node
    graph = add_node(graph, node_id=seed_id, node_type="seed", label=seed_label)

    # Add claim node
    graph = add_node(graph, node_id=claim_id, node_type="claim", label=claim_label)

    # Add seed_generated_claim edge
    graph = add_edge(
        graph,
        source_id=seed_id,
        target_id=claim_id,
        edge_type="seed_generated_claim",
    )

    # Optionally add evidence_gap
    if evidence_gap_id is not None:
        graph = add_node(
            graph,
            node_id=evidence_gap_id,
            node_type="evidence_gap",
            label=f"Evidence gap for {claim_label}",
        )
        graph = add_edge(
            graph,
            source_id=claim_id,
            target_id=evidence_gap_id,
            edge_type="claim_has_evidence_gap",
        )

    # Optionally add falsification_target
    if falsification_target_id is not None:
        graph = add_node(
            graph,
            node_id=falsification_target_id,
            node_type="falsification_target",
            label=f"Falsification target for {claim_label}",
        )
        graph = add_edge(
            graph,
            source_id=claim_id,
            target_id=falsification_target_id,
            edge_type="claim_has_falsification_target",
        )

    return graph
