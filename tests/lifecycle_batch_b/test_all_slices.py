"""Batch L3-B lifecycle shell tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.lifecycle.no_authority import check_lifecycle_import_fences
from hg_core.lifecycle_batch_b.checks import L3_B_SLICES, run_lifecycle_batch_b_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_lifecycle_slices_green() -> None:
    result = run_lifecycle_batch_b_checks(WORKSPACE, slice="all")
    assert result["ok"], result.get("critical_failures", result)


def test_each_slice_green() -> None:
    for name in L3_B_SLICES:
        result = run_lifecycle_batch_b_checks(WORKSPACE, slice=name)
        assert result["ok"], (name, result)


def test_unsupported_slice_fails_closed() -> None:
    result = run_lifecycle_batch_b_checks(WORKSPACE, slice="els")
    assert not result["ok"]
    assert "unsupported_slice" in result["critical_failures"]


def test_lifecycle_import_fences_clean() -> None:
    ok, failures = check_lifecycle_import_fences()
    assert ok, failures
