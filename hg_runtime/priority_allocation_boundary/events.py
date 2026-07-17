"""PAB planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.control_cluster.rtc_design import control_rtc_event

PAB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    control_rtc_event("PAB_PRIORITY_SIGNAL_RECORDED"),
    control_rtc_event("PAB_PRIORITY_ASSESSMENT_RECORDED"),
    control_rtc_event("PAB_ALLOCATION_RECOMMENDED"),
    control_rtc_event("PAB_PRIORITY_AS_PERMISSION_CONTAINED"),
    control_rtc_event("PAB_STALE_PRIORITY_REFUSED"),
    control_rtc_event("PAB_SIGNAL_REFUSED"),
    control_rtc_event("PAB_CONTAINMENT_WAIVED_RECORDED"),
)


def planned_pab_event_refs() -> tuple[dict[str, Any], ...]:
    return PAB_EVENT_REFS


__all__ = ["PAB_EVENT_REFS", "planned_pab_event_refs"]
