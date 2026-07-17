"""RIB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.rib_cluster.rtc_design import rib_rtc_event

RIB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    rib_rtc_event("RIB_SPAWN_REQUEST_RECORDED"),
    rib_rtc_event("RIB_INHERITANCE_DECISION_RECORDED"),
    rib_rtc_event("RIB_CHILD_BOOTSTRAP_PACKET_CREATED"),
    rib_rtc_event("RIB_CHILD_SPAWN_DENIED"),
    rib_rtc_event("RIB_CHILD_SPAWN_ATTEMPTED"),
    rib_rtc_event("RIB_CHILD_SPAWNED"),
    rib_rtc_event("RIB_CHILD_PARTIAL_SPAWN_RECORDED"),
    rib_rtc_event("RIB_CHILD_FAILED_SPAWN_RECORDED"),
    rib_rtc_event("RIB_CHILD_ROLLBACK_REQUESTED"),
    rib_rtc_event("RIB_CHILD_ROLLBACK_COMPLETED"),
    rib_rtc_event("RIB_CHILD_LIFECYCLE_RECEIPT_CREATED"),
    rib_rtc_event("RIB_PARENT_CHILD_AUTHORITY_SEPARATED"),
    rib_rtc_event("RIB_INHERITED_PERMISSION_REFUSED"),
    rib_rtc_event("RIB_INHERITED_IDENTITY_REFUSED"),
    rib_rtc_event("RIB_AUTHORITY_CONVERSION_CONTAINED"),
    rib_rtc_event("RIB_SIGNAL_REFUSED"),
)


def planned_rib_event_refs() -> tuple[dict[str, Any], ...]:
    return RIB_EVENT_REFS


__all__ = ["RIB_EVENT_REFS", "planned_rib_event_refs"]
