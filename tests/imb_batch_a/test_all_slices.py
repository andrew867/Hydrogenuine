"""Batch IMB-A shell tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.imb_batch_a.checks import IMB_A_SLICES, run_imb_batch_a_checks
from hg_core.imb_cluster.no_authority import check_imb_import_fences

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_imb_a_slices_green() -> None:
    result = run_imb_batch_a_checks(WORKSPACE, slice="all")
    assert result["ok"], result.get("critical_failures", result)


def test_each_slice_green() -> None:
    for name in IMB_A_SLICES:
        result = run_imb_batch_a_checks(WORKSPACE, slice=name)
        assert result["ok"], (name, result)


def test_unsupported_slice_fails_closed() -> None:
    result = run_imb_batch_a_checks(WORKSPACE, slice="ori")
    assert not result["ok"]
    assert "unsupported_slice" in result["critical_failures"]


def test_imb_import_fences_clean() -> None:
    ok, failures = check_imb_import_fences()
    assert ok, failures
