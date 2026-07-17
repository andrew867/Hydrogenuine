"""MBS cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.mbs_cluster.rtc_design import mbs_rtc_event

MBS_EVENT_REFS: tuple[dict[str, Any], ...] = (
        mbs_rtc_event("MBS_REQUEST_RECORDED"),
mbs_rtc_event("MBS_ENVELOPE_VALIDATED"),
mbs_rtc_event("MBS_ROUTE_RECOMMENDED"),
mbs_rtc_event("MBS_PRESSURE_OBSERVED"),
mbs_rtc_event("MBS_RECEIPT_CREATED"),
mbs_rtc_event("MBS_AUTHORITY_CONVERSION_REFUSED"),
mbs_rtc_event("MBS_FAILED_CLOSED"),
)


def planned_mbs_event_refs() -> tuple[dict[str, Any], ...]:
    return MBS_EVENT_REFS


__all__ = ["MBS_EVENT_REFS", "planned_mbs_event_refs"]
