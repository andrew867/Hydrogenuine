"""P7-B batch shell tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.p7_batch_b.checks import P7_B_SLICES, run_p7_batch_b_checks
from hg_core.embodiment_oea_cluster.events import planned_eog_event_refs
from hg_core.embodiment_oea_cluster.no_authority import check_eog_import_fences
from hg_core.embodiment_oea_cluster.rtc_design import validate_eog_rtc_event_design

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_p7_b_slices_green() -> None:
    result = run_p7_batch_b_checks(WORKSPACE, slice="all")
    assert result["ok"], result.get("critical_failures", result)


def test_each_slice_green() -> None:
    for name in P7_B_SLICES:
        result = run_p7_batch_b_checks(WORKSPACE, slice=name)
        assert result["ok"], (name, result)


def test_unsupported_slice_fails_closed() -> None:
    result = run_p7_batch_b_checks(WORKSPACE, slice="exciton")
    assert not result["ok"]
    assert "unsupported_slice" in result["critical_failures"]


def test_eog_import_fences_clean() -> None:
    ok, failures = check_eog_import_fences()
    assert ok, failures


def test_planned_rtc_events_valid() -> None:
    valid, failures = validate_eog_rtc_event_design(planned_eog_event_refs())
    assert valid, failures
    assert len(planned_eog_event_refs()) >= 14
