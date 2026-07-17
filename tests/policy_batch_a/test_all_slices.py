"""Batch P1-A policy safety shell tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.policy_batch_a.checks import P1_A_SLICES, run_policy_batch_a_checks
from hg_core.policy_safety.no_authority import check_policy_import_fences

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_policy_slices_green() -> None:
    result = run_policy_batch_a_checks(WORKSPACE, slice="all")
    assert result["ok"], result.get("critical_failures", result)


def test_each_slice_green() -> None:
    for name in P1_A_SLICES:
        result = run_policy_batch_a_checks(WORKSPACE, slice=name)
        assert result["ok"], (name, result)


def test_unsupported_slice_fails_closed() -> None:
    result = run_policy_batch_a_checks(WORKSPACE, slice="fce")
    assert not result["ok"]
    assert "unsupported_slice" in result["critical_failures"]


def test_policy_import_fences_clean() -> None:
    ok, failures = check_policy_import_fences()
    assert ok, failures
