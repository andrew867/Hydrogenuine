"""
Tests for Visualization Phase 6: advanced (timeline playback, causal graph, export, WCAG a11y).
"""
from pathlib import Path

import pytest

from hg_core.viz import (
    get_viz_timeline_playback,
    get_viz_causal_graph,
    get_viz_export,
    get_viz_a11y_metadata,
    adapt_timeline_playback,
    adapt_causal_graph,
    adapt_viz_export,
    adapt_a11y_metadata,
)


def test_get_viz_timeline_playback_shape(tmp_path: Path) -> None:
    """Timeline playback returns items, min_ts, max_ts, has_more."""
    out = get_viz_timeline_playback(tmp_path, limit=50)
    assert "items" in out
    assert "min_ts" in out
    assert "max_ts" in out
    assert "has_more" in out
    assert isinstance(out["items"], list)


def test_get_viz_causal_graph_shape(tmp_path: Path) -> None:
    """Causal graph returns nodes and edges."""
    out = get_viz_causal_graph(tmp_path, limit=20)
    assert "nodes" in out
    assert "edges" in out
    assert isinstance(out["nodes"], list)
    assert isinstance(out["edges"], list)


def test_get_viz_export_graph(tmp_path: Path) -> None:
    """Export type graph returns graph key."""
    out = get_viz_export(tmp_path, export_type="graph", limit=10)
    assert out["export_type"] == "graph"
    assert "graph" in out
    assert "nodes" in out["graph"]
    assert "edges" in out["graph"]


def test_get_viz_export_timeline(tmp_path: Path) -> None:
    """Export type timeline returns timeline key."""
    out = get_viz_export(tmp_path, export_type="timeline", limit=10)
    assert out["export_type"] == "timeline"
    assert "timeline" in out
    assert "items" in out["timeline"]


def test_get_viz_export_full(tmp_path: Path) -> None:
    """Export type full returns graph, timeline, data_map, trust_bands."""
    out = get_viz_export(tmp_path, export_type="full", limit=5)
    assert out["export_type"] == "full"
    assert "graph" in out
    assert "timeline" in out
    assert "data_map" in out
    assert "trust_bands" in out


def test_get_viz_a11y_metadata_shape() -> None:
    """A11y metadata returns ARIA roles and template."""
    out = get_viz_a11y_metadata()
    assert isinstance(out, dict)
    assert "node_role" in out
    assert "graph_role" in out
    assert "live_region_summary_template" in out


def test_adapt_timeline_playback(tmp_path: Path) -> None:
    """Adapter timeline playback returns items and ts bounds."""
    out = adapt_timeline_playback(tmp_path, limit=10)
    assert "items" in out
    assert "min_ts" in out
    assert "max_ts" in out


def test_adapt_causal_graph(tmp_path: Path) -> None:
    """Adapter causal graph returns nodes and edges."""
    out = adapt_causal_graph(tmp_path, limit=10)
    assert "nodes" in out
    assert "edges" in out


def test_adapt_viz_export(tmp_path: Path) -> None:
    """Adapter viz export returns export_type and payload."""
    out = adapt_viz_export(tmp_path, export_type="graph", limit=5)
    assert "export_type" in out
    assert "graph" in out


def test_adapt_a11y_metadata() -> None:
    """Adapter a11y metadata returns dict (no args)."""
    out = adapt_a11y_metadata()
    assert "graph_aria_label" in out
    assert "focus_order_hint" in out
