"""Observer active run tests."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.exciton.soak_watchtower import build_soak_watchtower


def test_watchtower_includes_active_run_verdict():
    wt = build_soak_watchtower()
    assert "active_run_verdict" in wt or wt.get("active") is False
