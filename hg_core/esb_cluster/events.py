"""ESB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.esb_cluster.rtc_design import esb_rtc_event

ESB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    esb_rtc_event("ESB_REQUEST_RECORDED"),
    esb_rtc_event("ESB_ENVELOPE_VALIDATED"),
    esb_rtc_event("ESB_ROUTE_RECOMMENDED"),
    esb_rtc_event("ESB_PRESSURE_OBSERVED"),
    esb_rtc_event("ESB_RECEIPT_CREATED"),
    esb_rtc_event("ESB_AUTHORITY_CONVERSION_REFUSED"),
    esb_rtc_event("ESB_FAILED_CLOSED"),
)


def planned_esb_event_refs() -> tuple[dict[str, Any], ...]:
    return ESB_EVENT_REFS


__all__ = ["ESB_EVENT_REFS", "planned_esb_event_refs"]
