"""REB batch shell tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.reb_batch_a.checks import REB_A_SLICES, run_reb_batch_a_checks
from hg_core.reb_cluster.events import planned_reb_event_refs
from hg_core.reb_cluster.no_authority import check_reb_import_fences
from hg_core.reb_cluster.rtc_design import validate_reb_rtc_event_design

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_reb_a_slices_green() -> None:
    result = run_reb_batch_a_checks(WORKSPACE, slice="all")
    assert result["ok"], result.get("critical_failures", result)


def test_each_slice_green() -> None:
    for name in REB_A_SLICES:
        result = run_reb_batch_a_checks(WORKSPACE, slice=name)
        assert result["ok"], (name, result)


def test_unsupported_slice_fails_closed() -> None:
    result = run_reb_batch_a_checks(WORKSPACE, slice="rib")
    assert not result["ok"]
    assert "unsupported_slice" in result["critical_failures"]


def test_reb_import_fences_clean() -> None:
    ok, failures = check_reb_import_fences()
    assert ok, failures


def test_planned_rtc_events_valid() -> None:
    valid, failures = validate_reb_rtc_event_design(planned_reb_event_refs())
    assert valid, failures
    assert len(planned_reb_event_refs()) >= 16
