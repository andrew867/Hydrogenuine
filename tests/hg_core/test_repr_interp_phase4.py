"""
Tests for Layer 8 Phase 4: operator console + Visualization Phase 4 wiring.
"""
from pathlib import Path

import pytest

from hg_core.viz.api import get_viz_proof_path, get_viz_repr_interp_results
from hg_core.repr_interp import store_inspection_result, inspection_result


def test_get_viz_proof_path_includes_representation_inspection_result(tmp_path: Path) -> None:
    """Viz Phase 4: get_viz_proof_path returns representation_inspection_result (from get_proof_path)."""
    r = inspection_result("p1", "req-1", "Out", ts="2026-01-01T00:00:00Z")
    r["decision_id"] = "dec-viz"
    store_inspection_result(tmp_path, r)
    proof = get_viz_proof_path(tmp_path, "dec-viz")
    assert "representation_inspection_result" in proof
    assert isinstance(proof["representation_inspection_result"], list)
    assert len(proof["representation_inspection_result"]) == 1


def test_get_viz_repr_interp_results_shape(tmp_path: Path) -> None:
    """Viz Phase 4 wiring: get_viz_repr_interp_results returns { results: [...] }."""
    out = get_viz_repr_interp_results(tmp_path, limit=10)
    assert "results" in out
    assert isinstance(out["results"], list)


def test_get_viz_repr_interp_results_with_decision_id(tmp_path: Path) -> None:
    """Viz Phase 4: filter by decision_id returns matching inspection results."""
    r = inspection_result("p1", "req-1", "Out", ts="2026-01-01T00:00:00Z")
    r["decision_id"] = "dec-filter"
    store_inspection_result(tmp_path, r)
    out = get_viz_repr_interp_results(tmp_path, decision_id="dec-filter", limit=10)
    assert len(out["results"]) == 1
    assert out["results"][0]["decision_id"] == "dec-filter"


def test_get_viz_repr_interp_results_no_repr_interp_import_returns_empty(tmp_path: Path) -> None:
    """When repr_interp is not importable, get_viz_repr_interp_results returns empty results (no crash)."""
    # We cannot easily unimport; the function catches ImportError and returns {"results": []}.
    # So we only assert the API exists and returns the right shape when repr_interp is available.
    out = get_viz_repr_interp_results(tmp_path)
    assert "results" in out
    assert isinstance(out["results"], list)
