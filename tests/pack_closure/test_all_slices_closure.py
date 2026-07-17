"""Batch CT-B all-slices pack closure tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.pack_closure.checks import CT_B_SLICE_PACKS, run_pack_closure_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_pack_closure_slices_green() -> None:
    result = run_pack_closure_checks(WORKSPACE, pack="all")
    assert result["ok"], result.get("critical_failures", result)
    assert set(result["slices"]) == set(CT_B_SLICE_PACKS)
    for name in CT_B_SLICE_PACKS:
        assert result["slices"][name]["ok"], (name, result["slices"][name])
