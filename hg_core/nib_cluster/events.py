"""NIB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.nib_cluster.rtc_design import nib_rtc_event

NIB_EVENT_REFS: tuple[dict[str, Any], ...] = (
        nib_rtc_event("NIB_INTAKE_REQUEST_RECORDED"),
nib_rtc_event("NIB_SOURCE_CLASSIFIED"),
nib_rtc_event("NIB_NUTRIENT_CLASSIFIED"),
nib_rtc_event("NIB_POISON_SIGNAL_RECORDED"),
nib_rtc_event("NIB_QUARANTINE_DECISION_RECORDED"),
nib_rtc_event("NIB_INTAKE_REFUSED"),
nib_rtc_event("NIB_ROUTE_TO_DAB_RECOMMENDED"),
nib_rtc_event("NIB_AUTHORITY_CONVERSION_REFUSED"),
nib_rtc_event("NIB_FAILED_CLOSED"),
)


def planned_nib_event_refs() -> tuple[dict[str, Any], ...]:
    return NIB_EVENT_REFS


__all__ = ["NIB_EVENT_REFS", "planned_nib_event_refs"]

