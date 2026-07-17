"""
Tests for Visualization Phase 2: graph and relationship views (DAG, ledger stream, delegation, impact graph).
"""
from pathlib import Path

import pytest

from hg_core.viz import (
    get_viz_impact_graph,
    get_viz_ledger_stream,
    get_viz_delegation_graph,
    get_viz_dag,
    adapt_impact_graph,
    adapt_ledger_stream,
    adapt_delegation_graph,
    adapt_dag_view,
    adapt_dag_runs_list,
    adapt_dag_run_graph,
)


def test_get_viz_impact_graph_shape(tmp_path: Path) -> None:
    """Impact graph API returns { nodes, edges }."""
    out = get_viz_impact_graph(tmp_path, limit=10)
    assert "nodes" in out
    assert "edges" in out
    assert isinstance(out["nodes"], list)
    assert isinstance(out["edges"], list)


def test_get_viz_impact_graph_node_shape(tmp_path: Path) -> None:
    """Impact graph nodes have id, type and optional evidence_refs."""
    out = get_viz_impact_graph(tmp_path, limit=5)
    for node in out["nodes"]:
        assert "id" in node
        assert "type" in node
        if "evidence_refs" in node:
            for ref in node["evidence_refs"]:
                assert "id" in ref


def test_get_viz_ledger_stream_shape(tmp_path: Path) -> None:
    """Ledger stream returns { items, has_more }."""
    out = get_viz_ledger_stream(tmp_path, limit=10)
    assert "items" in out
    assert "has_more" in out
    assert isinstance(out["items"], list)
    assert isinstance(out["has_more"], bool)


def test_get_viz_ledger_stream_item_shape(tmp_path: Path) -> None:
    """Stream items have event_id, action, ts, scope."""
    out = get_viz_ledger_stream(tmp_path, limit=5)
    for item in out["items"]:
        assert "event_id" in item
        assert "action" in item
        assert "ts" in item
        assert "scope" in item


def test_get_viz_delegation_graph_shape(tmp_path: Path) -> None:
    """Delegation graph returns { nodes, edges }."""
    out = get_viz_delegation_graph(tmp_path, limit=20)
    assert "nodes" in out
    assert "edges" in out
    assert isinstance(out["nodes"], list)
    assert isinstance(out["edges"], list)


def test_get_viz_delegation_graph_node_types(tmp_path: Path) -> None:
    """Delegation nodes are handoff or work_item only."""
    out = get_viz_delegation_graph(tmp_path, limit=50)
    for node in out["nodes"]:
        assert node.get("type") in ("handoff", "work_item")


def test_get_viz_dag_runs_shape(tmp_path: Path) -> None:
    """DAG view returns runs list and optional graph."""
    out = get_viz_dag(tmp_path, runs_limit=10)
    assert "runs" in out
    assert isinstance(out["runs"], list)


def test_get_viz_dag_with_run_id(tmp_path: Path) -> None:
    """DAG view with run_id includes graph."""
    out = get_viz_dag(tmp_path, run_id="nonexistent-run", runs_limit=5)
    assert "runs" in out
    assert "graph" in out
    assert "nodes" in out["graph"]
    assert "edges" in out["graph"]


def test_adapt_impact_graph_shape(tmp_path: Path) -> None:
    """Impact adapter returns { nodes, edges }."""
    out = adapt_impact_graph(tmp_path, limit=10)
    assert "nodes" in out
    assert "edges" in out


def test_adapt_ledger_stream_shape(tmp_path: Path) -> None:
    """Ledger stream adapter returns { items, has_more }."""
    out = adapt_ledger_stream(tmp_path, limit=5)
    assert "items" in out
    assert "has_more" in out


def test_adapt_delegation_graph_shape(tmp_path: Path) -> None:
    """Delegation adapter returns { nodes, edges }."""
    out = adapt_delegation_graph(tmp_path, limit=10)
    assert "nodes" in out
    assert "edges" in out


def test_adapt_dag_runs_list(tmp_path: Path) -> None:
    """DAG runs list returns list of run dicts."""
    runs = adapt_dag_runs_list(tmp_path, limit=5)
    assert isinstance(runs, list)
    for r in runs:
        assert "run_id" in r
        assert "graph_id" in r
        assert "status" in r


def test_adapt_dag_run_graph_missing_run(tmp_path: Path) -> None:
    """DAG run graph for missing run returns empty nodes and edges."""
    out = adapt_dag_run_graph(tmp_path, "no-such-run")
    assert out["nodes"] == []
    assert out["edges"] == []


def test_adapt_dag_view_combined(tmp_path: Path) -> None:
    """DAG view returns runs and optional graph."""
    out = adapt_dag_view(tmp_path, runs_limit=5)
    assert "runs" in out
    out2 = adapt_dag_view(tmp_path, run_id="x", runs_limit=5)
    assert "runs" in out2
    assert "graph" in out2
    assert "nodes" in out2["graph"]
    assert "edges" in out2["graph"]
