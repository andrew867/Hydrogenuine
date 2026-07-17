"""Batch C6-A control cluster shell tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.control_cluster.no_authority import check_control_import_fences
from hg_core.control_batch_a.checks import C6_A_SLICES, run_control_batch_a_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_control_a_slices_green() -> None:
    result = run_control_batch_a_checks(WORKSPACE, slice="all")
    assert result["ok"], result.get("critical_failures", result)


def test_each_slice_green() -> None:
    for name in C6_A_SLICES:
        result = run_control_batch_a_checks(WORKSPACE, slice=name)
        assert result["ok"], (name, result)


def test_unsupported_slice_fails_closed() -> None:
    result = run_control_batch_a_checks(WORKSPACE, slice="neg")
    assert not result["ok"]
    assert "unsupported_slice" in result["critical_failures"]


def test_control_import_fences_clean() -> None:
    ok, failures = check_control_import_fences()
    assert ok, failures
