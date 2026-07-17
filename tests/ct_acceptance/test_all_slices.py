"""Batch CT-C all-slices acceptance tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.ct_acceptance.checks import CT_C_SLICES, run_ct_acceptance_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_acceptance_slices_green() -> None:
    result = run_ct_acceptance_checks(WORKSPACE, slice="all")
    assert result["ok"], result.get("critical_failures", result)
    assert set(result["slices"]) == {"reconcile", "milestone", "full"}
    for name in CT_C_SLICES:
        if name == "all":
            continue
        assert result["slices"][name]["ok"], (name, result["slices"][name])


def test_unsupported_slice_fails_closed() -> None:
    result = run_ct_acceptance_checks(WORKSPACE, slice="organism_runtime")
    assert not result["ok"]
    assert "unsupported_slice" in result["critical_failures"]
