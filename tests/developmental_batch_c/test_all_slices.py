"""Batch D4-C developmental shell tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.developmental.no_authority import check_developmental_import_fences
from hg_core.developmental_batch_c.checks import D4_C_SLICES, run_developmental_batch_c_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_developmental_slices_green() -> None:
    result = run_developmental_batch_c_checks(WORKSPACE, slice="all")
    assert result["ok"], result.get("critical_failures", result)


def test_each_slice_green() -> None:
    for name in D4_C_SLICES:
        result = run_developmental_batch_c_checks(WORKSPACE, slice=name)
        assert result["ok"], (name, result)


def test_unsupported_slice_fails_closed() -> None:
    result = run_developmental_batch_c_checks(WORKSPACE, slice="els")
    assert not result["ok"]
    assert "unsupported_slice" in result["critical_failures"]


def test_developmental_import_fences_clean() -> None:
    ok, failures = check_developmental_import_fences()
    assert ok, failures
