"""ISB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.isb_cluster.rtc_design import isb_rtc_event

ISB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    isb_rtc_event("ISB_REQUEST_RECORDED"),
    isb_rtc_event("ISB_ENVELOPE_VALIDATED"),
    isb_rtc_event("ISB_ROUTE_RECOMMENDED"),
    isb_rtc_event("ISB_PRESSURE_OBSERVED"),
    isb_rtc_event("ISB_RECEIPT_CREATED"),
    isb_rtc_event("ISB_AUTHORITY_CONVERSION_REFUSED"),
    isb_rtc_event("ISB_FAILED_CLOSED"),
)


def planned_isb_event_refs() -> tuple[dict[str, Any], ...]:
    return ISB_EVENT_REFS


__all__ = ["ISB_EVENT_REFS", "planned_isb_event_refs"]
