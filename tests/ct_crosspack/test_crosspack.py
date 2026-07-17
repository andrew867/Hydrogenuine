"""CT-X1–X5 cross-pack integration tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.ct_crosspack.harness import run_all_crosspack_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_ct_x1_through_x5_harness_green() -> None:
    result = run_all_crosspack_checks(WORKSPACE)
    assert result["ok"], result["checks"]
