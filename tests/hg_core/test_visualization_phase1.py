"""
Tests for Visualization Phase 1: unified schema, read-only viz API, evidence_refs, adapters.
"""
from pathlib import Path

import pytest

from hg_core.viz import (
    VIZ_NODE_TYPES,
    VIZ_EDGE_TYPES,
    evidence_ref,
    normalize_evidence_refs,
    viz_node,
    viz_edge,
    get_viz_graph,
    get_viz_evidence_refs,
    adapt_materializer_graph,
    adapt_ledger_events_to_nodes,
)


def test_unified_schema_node_types():
    assert "work_item" in VIZ_NODE_TYPES
    assert "decision" in VIZ_NODE_TYPES
    assert "event" in VIZ_NODE_TYPES


def test_unified_schema_edge_types():
    assert "based_on" in VIZ_EDGE_TYPES
    assert "evidence" in VIZ_EDGE_TYPES


def test_evidence_ref():
    r = evidence_ref("e1", "event_id")
    assert r["id"] == "e1"
    assert r["type"] == "event_id"


def test_normalize_evidence_refs():
    assert normalize_evidence_refs([]) == []
    assert normalize_evidence_refs(["id1"]) == [{"id": "id1", "type": "event_id"}]
    assert normalize_evidence_refs([{"id": "id2", "type": "event_id"}]) == [
        {"id": "id2", "type": "event_id"}
    ]


def test_viz_node():
    n = viz_node("n1", "work_item", {"title": "x"}, [evidence_ref("e1")])
    assert n["id"] == "n1"
    assert n["type"] == "work_item"
    assert n["title"] == "x"
    assert n["evidence_refs"] == [{"id": "e1", "type": "event_id"}]


def test_viz_edge():
    e = viz_edge("a", "b", "based_on", [evidence_ref("e1")])
    assert e["from"] == "a"
    assert e["to"] == "b"
    assert e["type"] == "based_on"
    assert e["evidence_refs"] == [{"id": "e1", "type": "event_id"}]


def test_get_viz_graph_shape(tmp_path: Path):
    """API returns { nodes, edges } with list shape."""
    out = get_viz_graph(tmp_path, limit=10)
    assert "nodes" in out
    assert "edges" in out
    assert isinstance(out["nodes"], list)
    assert isinstance(out["edges"], list)


def test_get_viz_graph_evidence_refs_on_nodes(tmp_path: Path):
    """If graph has nodes with evidence_refs, they are normalized in output."""
    out = get_viz_graph(tmp_path, limit=50)
    for node in out["nodes"]:
        assert "id" in node
        assert "type" in node
        if "evidence_refs" in node:
            for ref in node["evidence_refs"]:
                assert "id" in ref


def test_get_viz_evidence_refs_no_node_id(tmp_path: Path):
    """Without node_id returns list (possibly empty)."""
    refs = get_viz_evidence_refs(tmp_path)
    assert isinstance(refs, list)


def test_get_viz_evidence_refs_with_node_id(tmp_path: Path):
    """With node_id returns list (empty if node not in graph)."""
    refs = get_viz_evidence_refs(tmp_path, node_id="nonexistent")
    assert refs == []


def test_adapt_materializer_graph_shape(tmp_path: Path):
    """Materializer adapter returns { nodes, edges }."""
    out = adapt_materializer_graph(tmp_path, limit=10)
    assert "nodes" in out
    assert "edges" in out
    assert isinstance(out["nodes"], list)
    assert isinstance(out["edges"], list)


def test_adapt_ledger_events_to_nodes_shape(tmp_path: Path):
    """Ledger adapter returns list of viz nodes."""
    nodes = adapt_ledger_events_to_nodes(tmp_path, limit=5)
    assert isinstance(nodes, list)
    for n in nodes:
        assert "id" in n
        assert "type" in n
        assert n.get("type") == "event"
        assert "evidence_refs" in n
