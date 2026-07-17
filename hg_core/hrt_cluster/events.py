"""HRT cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.hrt_cluster.rtc_design import hrt_rtc_event

HRT_EVENT_REFS: tuple[dict[str, Any], ...] = (
    hrt_rtc_event("HRT_REQUEST_RECORDED"),
    hrt_rtc_event("HRT_ENVELOPE_VALIDATED"),
    hrt_rtc_event("HRT_ROUTE_RECOMMENDED"),
    hrt_rtc_event("HRT_PRESSURE_OBSERVED"),
    hrt_rtc_event("HRT_RECEIPT_CREATED"),
    hrt_rtc_event("HRT_AUTHORITY_CONVERSION_REFUSED"),
    hrt_rtc_event("HRT_FAILED_CLOSED"),
)


def planned_hrt_event_refs() -> tuple[dict[str, Any], ...]:
    return HRT_EVENT_REFS


__all__ = ["HRT_EVENT_REFS", "planned_hrt_event_refs"]
