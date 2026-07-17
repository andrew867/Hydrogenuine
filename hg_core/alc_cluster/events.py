"""ALC cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.alc_cluster.rtc_design import alc_rtc_event

ALC_EVENT_REFS: tuple[dict[str, Any], ...] = (
    alc_rtc_event("ALC_REQUEST_RECORDED"),
    alc_rtc_event("ALC_ENVELOPE_VALIDATED"),
    alc_rtc_event("ALC_ROUTE_RECOMMENDED"),
    alc_rtc_event("ALC_PRESSURE_OBSERVED"),
    alc_rtc_event("ALC_RECEIPT_CREATED"),
    alc_rtc_event("ALC_AUTHORITY_CONVERSION_REFUSED"),
    alc_rtc_event("ALC_FAILED_CLOSED"),
)


def planned_alc_event_refs() -> tuple[dict[str, Any], ...]:
    return ALC_EVENT_REFS


__all__ = ["ALC_EVENT_REFS", "planned_alc_event_refs"]
