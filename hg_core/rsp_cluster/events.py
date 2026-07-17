"""RSP cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.rsp_cluster.rtc_design import rsp_rtc_event

RSP_EVENT_REFS: tuple[dict[str, Any], ...] = (
    rsp_rtc_event("RSP_REQUEST_RECORDED"),
    rsp_rtc_event("RSP_ENVELOPE_VALIDATED"),
    rsp_rtc_event("RSP_ROUTE_RECOMMENDED"),
    rsp_rtc_event("RSP_PRESSURE_OBSERVED"),
    rsp_rtc_event("RSP_RECEIPT_CREATED"),
    rsp_rtc_event("RSP_AUTHORITY_CONVERSION_REFUSED"),
    rsp_rtc_event("RSP_FAILED_CLOSED"),
)


def planned_rsp_event_refs() -> tuple[dict[str, Any], ...]:
    return RSP_EVENT_REFS


__all__ = ["RSP_EVENT_REFS", "planned_rsp_event_refs"]
