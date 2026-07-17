"""Batch R2-C runtime context shell tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.runtime_context.no_authority import check_runtime_import_fences
from hg_core.runtime_context_batch_c.checks import R2_C_SLICES, run_runtime_context_batch_c_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_runtime_slices_green() -> None:
    result = run_runtime_context_batch_c_checks(WORKSPACE, slice="all")
    assert result["ok"], result.get("critical_failures", result)


def test_each_slice_green() -> None:
    for name in R2_C_SLICES:
        result = run_runtime_context_batch_c_checks(WORKSPACE, slice=name)
        assert result["ok"], (name, result)


def test_unsupported_slice_fails_closed() -> None:
    result = run_runtime_context_batch_c_checks(WORKSPACE, slice="sim")
    assert not result["ok"]
    assert "unsupported_slice" in result["critical_failures"]


def test_runtime_import_fences_clean() -> None:
    ok, failures = check_runtime_import_fences()
    assert ok, failures
