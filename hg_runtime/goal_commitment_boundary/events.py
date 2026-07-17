"""GCB planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.control_cluster.rtc_design import control_rtc_event

GCB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    control_rtc_event("GCB_GOAL_COMMITMENT_RECORDED"),
    control_rtc_event("GCB_GOAL_FIT_ASSESSED"),
    control_rtc_event("GCB_OUT_OF_SCOPE_PROPOSAL_RECORDED"),
    control_rtc_event("GCB_GOAL_AS_PERMISSION_CONTAINED"),
    control_rtc_event("GCB_EXPIRED_GOAL_REFUSED"),
    control_rtc_event("GCB_STALE_GOAL_REFUSED"),
    control_rtc_event("GCB_SIGNAL_REFUSED"),
    control_rtc_event("GCB_CONTAINMENT_WAIVED_RECORDED"),
    control_rtc_event("GCB_GOAL_REFRESH_RECOMMENDED"),
)


def planned_gcb_event_refs() -> tuple[dict[str, Any], ...]:
    return GCB_EVENT_REFS


__all__ = ["GCB_EVENT_REFS", "planned_gcb_event_refs"]
