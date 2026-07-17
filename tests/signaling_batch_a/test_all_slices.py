"""Batch S5-A signaling shell tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.signaling.no_authority import check_signaling_import_fences
from hg_core.signaling_batch_a.checks import S5_A_SLICES, run_signaling_batch_a_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_signaling_slices_green() -> None:
    result = run_signaling_batch_a_checks(WORKSPACE, slice="all")
    assert result["ok"], result.get("critical_failures", result)


def test_each_slice_green() -> None:
    for name in S5_A_SLICES:
        result = run_signaling_batch_a_checks(WORKSPACE, slice=name)
        assert result["ok"], (name, result)


def test_unsupported_slice_fails_closed() -> None:
    result = run_signaling_batch_a_checks(WORKSPACE, slice="els")
    assert not result["ok"]
    assert "unsupported_slice" in result["critical_failures"]


def test_signaling_import_fences_clean() -> None:
    ok, failures = check_signaling_import_fences()
    assert ok, failures
