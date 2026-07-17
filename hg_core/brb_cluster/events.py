"""BRB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.brb_cluster.rtc_design import brb_rtc_event

BRB_EVENT_REFS: tuple[dict[str, Any], ...] = (
        brb_rtc_event("BRB_BREATH_CYCLE_RECORDED"),
brb_rtc_event("BRB_TOKEN_PRESSURE_OBSERVED"),
brb_rtc_event("BRB_COMPUTE_PRESSURE_OBSERVED"),
brb_rtc_event("BRB_CADENCE_RECOMMENDED"),
brb_rtc_event("BRB_PAUSE_RECOMMENDED"),
brb_rtc_event("BRB_YIELD_RECOMMENDED"),
brb_rtc_event("BRB_REST_RECOMMENDED"),
brb_rtc_event("BRB_OVERBREATHING_WARNING_RECORDED"),
brb_rtc_event("BRB_AUTHORITY_CONVERSION_REFUSED"),
brb_rtc_event("BRB_FAILED_CLOSED"),
)


def planned_brb_event_refs() -> tuple[dict[str, Any], ...]:
    return BRB_EVENT_REFS


__all__ = ["BRB_EVENT_REFS", "planned_brb_event_refs"]

