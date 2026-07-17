"""
Tests for Visualization Phase 5: system-of-systems and dashboards (data map, operator widgets, deep-linking).
"""
from pathlib import Path

import pytest

from hg_core.viz import (
    get_viz_data_map,
    get_viz_operator_widgets,
    get_viz_deep_link,
    adapt_data_map,
    adapt_operator_widgets,
    adapt_deep_link,
)


def test_get_viz_data_map_shape(tmp_path: Path) -> None:
    """Data map returns sources list with id, type, link_params."""
    out = get_viz_data_map(tmp_path)
    assert isinstance(out, dict)
    assert "sources" in out
    assert isinstance(out["sources"], list)
    for s in out["sources"]:
        assert "id" in s
        assert "type" in s
        assert "link_params" in s


def test_get_viz_data_map_dag_runs_entry(tmp_path: Path) -> None:
    """Data map may include dag_runs if memory/automation/dag_runs exists."""
    (tmp_path / "memory" / "automation" / "dag_runs").mkdir(parents=True)
    out = get_viz_data_map(tmp_path)
    ids = [s["id"] for s in out["sources"]]
    assert any("dag" in i or "automation" in i for i in ids)


def test_get_viz_operator_widgets_shape(tmp_path: Path) -> None:
    """Operator widgets returns role, widgets list."""
    out = get_viz_operator_widgets(tmp_path, role="operator")
    assert "role" in out
    assert "widgets" in out
    assert isinstance(out["widgets"], list)


def test_get_viz_operator_widgets_viewer(tmp_path: Path) -> None:
    """Viewer role returns summary-style widgets."""
    out = get_viz_operator_widgets(tmp_path, role="viewer")
    assert out["role"] == "viewer"
    assert isinstance(out["widgets"], list)


def test_get_viz_deep_link_decision(tmp_path: Path) -> None:
    """Deep link for decision returns view decision_explainer and params."""
    out = get_viz_deep_link(tmp_path, "decision", "dec-1")
    assert out["view"] == "decision_explainer"
    assert out["params"].get("decision_id") == "dec-1"
    assert out.get("fragment") == "proof-path"


def test_get_viz_deep_link_incident(tmp_path: Path) -> None:
    """Deep link for incident returns view incident."""
    out = get_viz_deep_link(tmp_path, "incident", "inc-1")
    assert out["view"] == "incident"
    assert out["params"].get("incident_id") == "inc-1"


def test_get_viz_deep_link_run(tmp_path: Path) -> None:
    """Deep link for run returns view dag."""
    out = get_viz_deep_link(tmp_path, "run", "run-123")
    assert out["view"] == "dag"
    assert out["params"].get("run_id") == "run-123"


def test_adapt_data_map(tmp_path: Path) -> None:
    """Adapter data map returns sources."""
    out = adapt_data_map(tmp_path)
    assert "sources" in out


def test_adapt_operator_widgets(tmp_path: Path) -> None:
    """Adapter operator widgets returns dashboard dict."""
    out = adapt_operator_widgets(tmp_path, role="admin")
    assert "widgets" in out


def test_adapt_deep_link(tmp_path: Path) -> None:
    """Adapter deep link returns view and params."""
    out = adapt_deep_link(tmp_path, "work_item", "wi-1")
    assert out["view"] == "work_item"
    assert out["params"].get("work_item_id") == "wi-1"
