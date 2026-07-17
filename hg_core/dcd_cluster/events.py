"""DCD cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.dcd_cluster.rtc_design import dcd_rtc_event

DCD_EVENT_REFS: tuple[dict[str, Any], ...] = (
        dcd_rtc_event("DCD_DECOMMISSION_REQUEST_RECORDED"),
dcd_rtc_event("DCD_DECOMMISSION_RECORD_CREATED"),
dcd_rtc_event("DCD_CEMETERY_RECORD_CREATED"),
dcd_rtc_event("DCD_TOMBSTONE_RECEIPT_CREATED"),
dcd_rtc_event("DCD_BURIAL_RECEIPT_CREATED"),
dcd_rtc_event("DCD_GHOST_RESURRECTION_REFUSED"),
dcd_rtc_event("DCD_INHERITED_IDENTITY_REFUSED"),
dcd_rtc_event("DCD_PROTECTED_ARTIFACT_REFUSED"),
dcd_rtc_event("DCD_AUTHORITY_CONVERSION_REFUSED"),
dcd_rtc_event("DCD_FAILED_CLOSED"),
)


def planned_dcd_event_refs() -> tuple[dict[str, Any], ...]:
    return DCD_EVENT_REFS


__all__ = ["DCD_EVENT_REFS", "planned_dcd_event_refs"]

