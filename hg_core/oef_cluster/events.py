"""OEF cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.oef_cluster.rtc_design import oef_rtc_event

OEF_EVENT_REFS: tuple[dict[str, Any], ...] = (
        oef_rtc_event("OEF_REQUEST_RECORDED"),
oef_rtc_event("OEF_ENVELOPE_VALIDATED"),
oef_rtc_event("OEF_ROUTE_RECOMMENDED"),
oef_rtc_event("OEF_PRESSURE_OBSERVED"),
oef_rtc_event("OEF_RECEIPT_CREATED"),
oef_rtc_event("OEF_AUTHORITY_CONVERSION_REFUSED"),
oef_rtc_event("OEF_FAILED_CLOSED"),
)


def planned_oef_event_refs() -> tuple[dict[str, Any], ...]:
    return OEF_EVENT_REFS


__all__ = ["OEF_EVENT_REFS", "planned_oef_event_refs"]
