"""TRB planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.control_cluster.rtc_design import control_rtc_event

TRB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    control_rtc_event("TRB_CALIBRATION_RECORDED"),
    control_rtc_event("TRB_RELIANCE_BOUNDARY_RECORDED"),
    control_rtc_event("TRB_TRUST_AS_TRUTH_CONTAINED"),
    control_rtc_event("TRB_CALIBRATION_AS_AUTHORITY_CONTAINED"),
    control_rtc_event("TRB_STALE_TRUST_REFUSED"),
    control_rtc_event("TRB_SIGNAL_REFUSED"),
    control_rtc_event("TRB_CONTAINMENT_WAIVED_RECORDED"),
)


def planned_trb_event_refs() -> tuple[dict[str, Any], ...]:
    return TRB_EVENT_REFS


__all__ = ["TRB_EVENT_REFS", "planned_trb_event_refs"]
