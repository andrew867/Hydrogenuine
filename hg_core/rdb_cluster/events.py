"""RDB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.rdb_cluster.rtc_design import rdb_rtc_event

RDB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    rdb_rtc_event("RDB_REQUEST_RECORDED"),
    rdb_rtc_event("RDB_ENVELOPE_VALIDATED"),
    rdb_rtc_event("RDB_ROUTE_RECOMMENDED"),
    rdb_rtc_event("RDB_PRESSURE_OBSERVED"),
    rdb_rtc_event("RDB_RECEIPT_CREATED"),
    rdb_rtc_event("RDB_AUTHORITY_CONVERSION_REFUSED"),
    rdb_rtc_event("RDB_FAILED_CLOSED"),
)


def planned_rdb_event_refs() -> tuple[dict[str, Any], ...]:
    return RDB_EVENT_REFS


__all__ = ["RDB_EVENT_REFS", "planned_rdb_event_refs"]
