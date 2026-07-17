"""CIR cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.cir_cluster.rtc_design import cir_rtc_event

CIR_EVENT_REFS: tuple[dict[str, Any], ...] = (
    cir_rtc_event("CIR_REQUEST_RECORDED"),
    cir_rtc_event("CIR_ENVELOPE_VALIDATED"),
    cir_rtc_event("CIR_ROUTE_RECOMMENDED"),
    cir_rtc_event("CIR_PRESSURE_OBSERVED"),
    cir_rtc_event("CIR_RECEIPT_CREATED"),
    cir_rtc_event("CIR_AUTHORITY_CONVERSION_REFUSED"),
    cir_rtc_event("CIR_FAILED_CLOSED"),
)


def planned_cir_event_refs() -> tuple[dict[str, Any], ...]:
    return CIR_EVENT_REFS


__all__ = ["CIR_EVENT_REFS", "planned_cir_event_refs"]
