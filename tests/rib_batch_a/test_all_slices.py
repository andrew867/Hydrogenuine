"""RIB batch shell tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.rib_batch_a.checks import RIB_A_SLICES, run_rib_batch_a_checks
from hg_core.rib_cluster.events import planned_rib_event_refs
from hg_core.rib_cluster.no_authority import check_rib_import_fences
from hg_core.rib_cluster.rtc_design import validate_rib_rtc_event_design

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_rib_a_slices_green() -> None:
    result = run_rib_batch_a_checks(WORKSPACE, slice="all")
    assert result["ok"], result.get("critical_failures", result)


def test_each_slice_green() -> None:
    for name in RIB_A_SLICES:
        result = run_rib_batch_a_checks(WORKSPACE, slice=name)
        assert result["ok"], (name, result)


def test_unsupported_slice_fails_closed() -> None:
    result = run_rib_batch_a_checks(WORKSPACE, slice="egi")
    assert not result["ok"]
    assert "unsupported_slice" in result["critical_failures"]


def test_rib_import_fences_clean() -> None:
    ok, failures = check_rib_import_fences()
    assert ok, failures


def test_planned_rtc_events_valid() -> None:
    valid, failures = validate_rib_rtc_event_design(planned_rib_event_refs())
    assert valid, failures
    assert len(planned_rib_event_refs()) >= 12
