"""ORI planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.ori_cluster.rtc_design import ori_rtc_event

ORI_EVENT_REFS: tuple[dict[str, Any], ...] = (
    ori_rtc_event("ORI_REVIEW_REQUEST_RECORDED"),
    ori_rtc_event("ORI_REVIEW_ITEM_CREATED"),
    ori_rtc_event("ORI_REVIEW_BATCH_CREATED"),
    ori_rtc_event("ORI_DEDUPLICATION_APPLIED"),
    ori_rtc_event("ORI_DUPLICATE_SUPPRESSED"),
    ori_rtc_event("ORI_PRIORITY_ASSIGNED"),
    ori_rtc_event("ORI_OPERATOR_OVERLOAD_SIGNAL_RECORDED"),
    ori_rtc_event("ORI_LOW_PRIORITY_DEFERRED"),
    ori_rtc_event("ORI_CRITICAL_REVIEW_ESCALATED"),
    ori_rtc_event("ORI_OPERATOR_RESPONSE_RECORDED"),
    ori_rtc_event("ORI_REVIEW_RECEIPT_CREATED"),
    ori_rtc_event("ORI_REVIEW_EXPIRED"),
    ori_rtc_event("ORI_SILENCE_POLICY_APPLIED"),
    ori_rtc_event("ORI_AUTHORITY_CONVERSION_CONTAINED"),
    ori_rtc_event("ORI_SIGNAL_REFUSED"),
)


def planned_ori_event_refs() -> tuple[dict[str, Any], ...]:
    return ORI_EVENT_REFS


_PRIORITY_EVENT_MAP: dict[str, str] = {
    "critical": "ORI_CRITICAL_REVIEW_ESCALATED",
    "urgent": "ORI_CRITICAL_REVIEW_ESCALATED",
    "high": "ORI_PRIORITY_ASSIGNED",
    "normal": "ORI_PRIORITY_ASSIGNED",
    "low": "ORI_LOW_PRIORITY_DEFERRED",
}


def priority_event(priority: str) -> str:
    return _PRIORITY_EVENT_MAP.get(priority, "ORI_PRIORITY_ASSIGNED")


__all__ = [
    "ORI_EVENT_REFS",
    "planned_ori_event_refs",
    "priority_event",
]
