"""Batch CT-B TIM-U4 boundary pack closure tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.pack_closure.checks import run_pack_closure_checks

WORKSPACE = Path(__file__).resolve().parents[2]


def test_tim_u4_closure_checks_green() -> None:
    result = run_pack_closure_checks(WORKSPACE, pack="tim_u4_boundary")
    assert result["ok"], result.get("critical_failures", result)


def test_tim_u4_boundary_honestly_defers_full_pack() -> None:
    result = run_pack_closure_checks(WORKSPACE, pack="tim_u4_boundary")
    assert result["full_pack_tim"]["status"] == "deferred_post_ct"
    assert result["full_pack_tim"]["slice"] == "TIM-U4"


def test_tim_u4_status_and_inventory_deferral_checks_pass() -> None:
    result = run_pack_closure_checks(WORKSPACE, pack="tim_u4_boundary")
    check_ids = {c["check_id"] for c in result["checks"]}
    assert "full_tim_honestly_deferred_in_status" in check_ids
    assert "full_tim_deferred_in_inventory" in check_ids
    by_id = {c["check_id"]: c for c in result["checks"]}
    assert by_id["full_tim_honestly_deferred_in_status"]["ok"]
    assert by_id["full_tim_deferred_in_inventory"]["ok"]
