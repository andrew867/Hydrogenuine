"""
Tests for Visualization Phase 3: trust and policy views (bands, budget, escrow, gating).
"""
from pathlib import Path

import pytest

from hg_core.viz import (
    get_viz_trust_bands,
    get_viz_budget_view,
    get_viz_escrow_view,
    get_viz_gating_view,
    adapt_trust_bands,
    adapt_budget_view,
    adapt_escrow_view,
    adapt_gating_view,
)


def test_get_viz_trust_bands_shape(tmp_path: Path) -> None:
    """Trust bands returns list of band dicts with band_index, name, max_action."""
    bands = get_viz_trust_bands(tmp_path)
    assert isinstance(bands, list)
    for b in bands:
        assert "band_index" in b
        assert "name" in b
        assert "max_action" in b


def test_get_viz_trust_bands_default_policy(tmp_path: Path) -> None:
    """Without policy file, default policy yields at least one band."""
    bands = get_viz_trust_bands(tmp_path)
    assert len(bands) >= 1
    assert bands[0]["band_index"] == 0


def test_get_viz_budget_view_shape(tmp_path: Path) -> None:
    """Budget view has policy_budget and operator_budgets."""
    out = get_viz_budget_view(tmp_path)
    assert "policy_budget" in out
    assert "operator_budgets" in out
    assert "default_limit" in out["policy_budget"]
    assert "hard" in out["policy_budget"]
    assert isinstance(out["operator_budgets"], list)


def test_get_viz_escrow_view_shape(tmp_path: Path) -> None:
    """Escrow view has lock_amount_default and high_impact_actions."""
    out = get_viz_escrow_view(tmp_path)
    assert "lock_amount_default" in out
    assert "high_impact_actions" in out
    assert isinstance(out["high_impact_actions"], list)


def test_get_viz_gating_view_shape(tmp_path: Path) -> None:
    """Gating view has trust_band_limits, require_approval_for_actions, high_impact_actions."""
    out = get_viz_gating_view(tmp_path)
    assert "trust_band_limits" in out
    assert "require_approval_for_actions" in out
    assert "high_impact_actions" in out
    assert isinstance(out["trust_band_limits"], dict)
    assert isinstance(out["require_approval_for_actions"], list)
    assert isinstance(out["high_impact_actions"], list)


def test_adapt_trust_bands(tmp_path: Path) -> None:
    """Adapter trust bands returns list."""
    bands = adapt_trust_bands(tmp_path)
    assert isinstance(bands, list)


def test_adapt_budget_view(tmp_path: Path) -> None:
    """Adapter budget view returns dict with policy_budget and operator_budgets."""
    out = adapt_budget_view(tmp_path)
    assert "policy_budget" in out
    assert "operator_budgets" in out


def test_adapt_escrow_view(tmp_path: Path) -> None:
    """Adapter escrow view returns dict."""
    out = adapt_escrow_view(tmp_path)
    assert "lock_amount_default" in out
    assert "high_impact_actions" in out


def test_adapt_gating_view(tmp_path: Path) -> None:
    """Adapter gating view returns dict with required keys."""
    out = adapt_gating_view(tmp_path)
    assert "trust_band_limits" in out
    assert "require_approval_for_actions" in out
    assert "high_impact_actions" in out
