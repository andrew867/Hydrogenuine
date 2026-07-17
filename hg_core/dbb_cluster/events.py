"""DBB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.dbb_cluster.rtc_design import dbb_rtc_event

DBB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    dbb_rtc_event("DBB_REQUEST_RECORDED"),
    dbb_rtc_event("DBB_ENVELOPE_VALIDATED"),
    dbb_rtc_event("DBB_ROUTE_RECOMMENDED"),
    dbb_rtc_event("DBB_PRESSURE_OBSERVED"),
    dbb_rtc_event("DBB_RECEIPT_CREATED"),
    dbb_rtc_event("DBB_AUTHORITY_CONVERSION_REFUSED"),
    dbb_rtc_event("DBB_FAILED_CLOSED"),
)


def planned_dbb_event_refs() -> tuple[dict[str, Any], ...]:
    return DBB_EVENT_REFS


__all__ = ["DBB_EVENT_REFS", "planned_dbb_event_refs"]
