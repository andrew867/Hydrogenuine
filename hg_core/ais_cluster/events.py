"""AIS cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.ais_cluster.rtc_design import ais_rtc_event

AIS_EVENT_REFS: tuple[dict[str, Any], ...] = (
        ais_rtc_event("AIS_REQUEST_RECORDED"),
ais_rtc_event("AIS_ENVELOPE_VALIDATED"),
ais_rtc_event("AIS_ROUTE_RECOMMENDED"),
ais_rtc_event("AIS_PRESSURE_OBSERVED"),
ais_rtc_event("AIS_RECEIPT_CREATED"),
ais_rtc_event("AIS_AUTHORITY_CONVERSION_REFUSED"),
ais_rtc_event("AIS_FAILED_CLOSED"),
)


def planned_ais_event_refs() -> tuple[dict[str, Any], ...]:
    return AIS_EVENT_REFS


__all__ = ["AIS_EVENT_REFS", "planned_ais_event_refs"]
