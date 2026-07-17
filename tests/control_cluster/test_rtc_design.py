"""Control cluster RTC design tests."""

from __future__ import annotations

from hg_core.control_cluster.rtc_design import (
    CONTROL_RTC_FAMILY,
    control_rtc_event,
    validate_control_rtc_event_design,
)
from hg_runtime.resource_scarcity_controller.events import planned_rsc_event_refs


def test_control_rtc_event_has_required_fields() -> None:
    event = control_rtc_event("RSC_TEST_EVENT")
    assert event["family"] == CONTROL_RTC_FAMILY
    assert event["cognition_eligible"] is False
    assert event["authority_fields"] is False
    assert event["redacted"] is True
    assert event["hashable"] is True


def test_planned_rsc_event_refs_are_complete_rtc_design() -> None:
    refs = planned_rsc_event_refs()
    valid, failures = validate_control_rtc_event_design(refs)
    assert valid, failures
    assert len(refs) >= 8
