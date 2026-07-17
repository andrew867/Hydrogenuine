"""BRS cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.brs_cluster.rtc_design import brs_rtc_event

BRS_EVENT_REFS: tuple[dict[str, Any], ...] = (
    brs_rtc_event("BRS_REQUEST_RECORDED"),
    brs_rtc_event("BRS_ENVELOPE_VALIDATED"),
    brs_rtc_event("BRS_ROUTE_RECOMMENDED"),
    brs_rtc_event("BRS_PRESSURE_OBSERVED"),
    brs_rtc_event("BRS_RECEIPT_CREATED"),
    brs_rtc_event("BRS_AUTHORITY_CONVERSION_REFUSED"),
    brs_rtc_event("BRS_FAILED_CLOSED"),
)


def planned_brs_event_refs() -> tuple[dict[str, Any], ...]:
    return BRS_EVENT_REFS


__all__ = ["BRS_EVENT_REFS", "planned_brs_event_refs"]
