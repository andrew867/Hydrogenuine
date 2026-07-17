"""Soak watchtower data."""

from __future__ import annotations

from hg_runtime.exciton.soak_watchtower import build_soak_watchtower


def test_watchtower_has_eta_fields():
    wt = build_soak_watchtower()
    assert "data_tier" in wt
    assert "observer_verdict" in wt
    if wt.get("active"):
        assert "next_cycle_eta_seconds" in wt
        assert "elapsed_minutes" in wt
