"""Batch EGI-A shell tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.egi_batch_a.checks import EGI_A_SLICES, run_egi_batch_a_checks
from hg_core.egi_cluster.no_authority import check_egi_import_fences
from hg_core.egi_cluster.rtc_design import validate_egi_rtc_event_design
from hg_core.egi_cluster.events import planned_egi_event_refs

WORKSPACE = Path(__file__).resolve().parents[2]


def test_all_egi_a_slices_green() -> None:
    result = run_egi_batch_a_checks(WORKSPACE, slice="all")
    assert result["ok"], result.get("critical_failures", result)


def test_each_slice_green() -> None:
    for name in EGI_A_SLICES:
        result = run_egi_batch_a_checks(WORKSPACE, slice=name)
        assert result["ok"], (name, result)


def test_unsupported_slice_fails_closed() -> None:
    result = run_egi_batch_a_checks(WORKSPACE, slice="erb")
    assert not result["ok"]
    assert "unsupported_slice" in result["critical_failures"]


def test_egi_import_fences_clean() -> None:
    ok, failures = check_egi_import_fences()
    assert ok, failures


def test_planned_rtc_events_valid() -> None:
    valid, failures = validate_egi_rtc_event_design(planned_egi_event_refs())
    assert valid, failures
    assert len(planned_egi_event_refs()) >= 12
