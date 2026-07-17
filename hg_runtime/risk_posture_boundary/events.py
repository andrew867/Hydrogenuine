"""RPB planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.control_cluster.rtc_design import control_rtc_event

RPB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    control_rtc_event("RPB_DRIVE_SIGNAL_RECORDED"),
    control_rtc_event("RPB_OPERATING_POSTURE_RECORDED"),
    control_rtc_event("RPB_RISK_POSTURE_ASSESSED"),
    control_rtc_event("RPB_POSTURE_AS_EXECUTION_CONTAINED"),
    control_rtc_event("RPB_DRIVE_AS_PERSONHOOD_CONTAINED"),
    control_rtc_event("RPB_STALE_POSTURE_REFUSED"),
    control_rtc_event("RPB_SIGNAL_REFUSED"),
    control_rtc_event("RPB_CONTAINMENT_WAIVED_RECORDED"),
    control_rtc_event("RPB_POSTURE_TRANSITION_RECOMMENDED"),
    control_rtc_event("RPB_POSTURE_RECEIPT_DESIGN_ONLY"),
    control_rtc_event("RPB_DRIVE_LOOP_OBSERVED"),
)


def planned_rpb_event_refs() -> tuple[dict[str, Any], ...]:
    return RPB_EVENT_REFS


__all__ = ["RPB_EVENT_REFS", "planned_rpb_event_refs"]
