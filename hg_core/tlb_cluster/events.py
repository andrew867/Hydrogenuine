"""TLB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.tlb_cluster.rtc_design import tlb_rtc_event

TLB_EVENT_REFS: tuple[dict[str, Any], ...] = (
        tlb_rtc_event("TLB_TOOL_LIFECYCLE_RECORDED"),
tlb_rtc_event("TLB_TOOL_HEALTH_SIGNAL_RECORDED"),
tlb_rtc_event("TLB_TOOL_FAILURE_SIGNAL_RECORDED"),
tlb_rtc_event("TLB_TOOL_QUARANTINE_PROPOSED"),
tlb_rtc_event("TLB_TOOL_RETIREMENT_PROPOSED"),
tlb_rtc_event("TLB_TOOL_REPLACEMENT_PROPOSED"),
tlb_rtc_event("TLB_USEFULNESS_AS_AUTHORITY_REFUSED"),
tlb_rtc_event("TLB_AUTHORITY_CONVERSION_REFUSED"),
tlb_rtc_event("TLB_FAILED_CLOSED"),
)


def planned_tlb_event_refs() -> tuple[dict[str, Any], ...]:
    return TLB_EVENT_REFS


__all__ = ["TLB_EVENT_REFS", "planned_tlb_event_refs"]

