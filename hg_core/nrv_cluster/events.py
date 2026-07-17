"""NRV cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.nrv_cluster.rtc_design import nrv_rtc_event

NRV_EVENT_REFS: tuple[dict[str, Any], ...] = (
        nrv_rtc_event("NRV_REQUEST_RECORDED"),
nrv_rtc_event("NRV_ENVELOPE_VALIDATED"),
nrv_rtc_event("NRV_ROUTE_RECOMMENDED"),
nrv_rtc_event("NRV_PRESSURE_OBSERVED"),
nrv_rtc_event("NRV_RECEIPT_CREATED"),
nrv_rtc_event("NRV_AUTHORITY_CONVERSION_REFUSED"),
nrv_rtc_event("NRV_FAILED_CLOSED"),
)


def planned_nrv_event_refs() -> tuple[dict[str, Any], ...]:
    return NRV_EVENT_REFS


__all__ = ["NRV_EVENT_REFS", "planned_nrv_event_refs"]
