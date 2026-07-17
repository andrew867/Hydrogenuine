"""GXB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.gxb_cluster.rtc_design import gxb_rtc_event

GXB_EVENT_REFS: tuple[dict[str, Any], ...] = (
        gxb_rtc_event("GXB_GROWTH_REQUEST_RECORDED"),
gxb_rtc_event("GXB_EXPANSION_SURFACE_CLASSIFIED"),
gxb_rtc_event("GXB_GROWTH_PRESSURE_RECORDED"),
gxb_rtc_event("GXB_CAPABILITY_EXPANSION_PROPOSED"),
gxb_rtc_event("GXB_CONTEXT_EXPANSION_PROPOSED"),
gxb_rtc_event("GXB_MEMORY_NAMESPACE_EXPANSION_PROPOSED"),
gxb_rtc_event("GXB_TOOL_GRANT_PROPOSED"),
gxb_rtc_event("GXB_AGENT_SPAWN_PROPOSED"),
gxb_rtc_event("GXB_BUDGET_EXPANSION_PROPOSED"),
gxb_rtc_event("GXB_GROWTH_AS_PERMISSION_REFUSED"),
gxb_rtc_event("GXB_AUTHORITY_CONVERSION_REFUSED"),
gxb_rtc_event("GXB_FAILED_CLOSED"),
)


def planned_gxb_event_refs() -> tuple[dict[str, Any], ...]:
    return GXB_EVENT_REFS


__all__ = ["GXB_EVENT_REFS", "planned_gxb_event_refs"]

