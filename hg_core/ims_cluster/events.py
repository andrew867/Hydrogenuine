"""IMS cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.ims_cluster.rtc_design import ims_rtc_event

IMS_EVENT_REFS: tuple[dict[str, Any], ...] = (
        ims_rtc_event("IMS_REQUEST_RECORDED"),
ims_rtc_event("IMS_ENVELOPE_VALIDATED"),
ims_rtc_event("IMS_ROUTE_RECOMMENDED"),
ims_rtc_event("IMS_PRESSURE_OBSERVED"),
ims_rtc_event("IMS_RECEIPT_CREATED"),
ims_rtc_event("IMS_AUTHORITY_CONVERSION_REFUSED"),
ims_rtc_event("IMS_FAILED_CLOSED"),
)


def planned_ims_event_refs() -> tuple[dict[str, Any], ...]:
    return IMS_EVENT_REFS


__all__ = ["IMS_EVENT_REFS", "planned_ims_event_refs"]
