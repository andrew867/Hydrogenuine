"""MIS planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.control_cluster.rtc_design import control_rtc_event

MIS_EVENT_REFS: tuple[dict[str, Any], ...] = (
    control_rtc_event("MIS_DRIFT_OBSERVED"),
    control_rtc_event("MIS_MISSION_REFRESH_RECOMMENDED"),
    control_rtc_event("MIS_GOAL_AS_AUTHORITY_CONTAINED"),
    control_rtc_event("MIS_STALE_DRIFT_REFUSED"),
    control_rtc_event("MIS_SIGNAL_REFUSED"),
    control_rtc_event("MIS_CONTAINMENT_WAIVED_RECORDED"),
    control_rtc_event("MIS_DRIFT_CONTAINED"),
)


def planned_mis_event_refs() -> tuple[dict[str, Any], ...]:
    return MIS_EVENT_REFS


__all__ = ["MIS_EVENT_REFS", "planned_mis_event_refs"]
