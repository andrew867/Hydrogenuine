"""RSC planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.control_cluster.rtc_design import control_rtc_event

RSC_EVENT_REFS: tuple[dict[str, Any], ...] = (
    control_rtc_event("RSC_RESOURCE_POSTURE_RECORDED"),
    control_rtc_event("RSC_SCARCITY_DETECTED"),
    control_rtc_event("RSC_COMPACTION_RECOMMENDED"),
    control_rtc_event("RSC_DEFER_RECOMMENDED"),
    control_rtc_event("RSC_SAFE_STOP_RECOMMENDED"),
    control_rtc_event("RSC_RESOURCE_BYPASS_CONTAINED"),
    control_rtc_event("RSC_SIGNAL_REFUSED"),
    control_rtc_event("RSC_CONTAINMENT_WAIVED_RECORDED"),
)


def planned_rsc_event_refs() -> tuple[dict[str, Any], ...]:
    return RSC_EVENT_REFS


__all__ = ["RSC_EVENT_REFS", "planned_rsc_event_refs"]
