"""BCP planned RTC event design — first safe slice, no emission."""

from __future__ import annotations

from typing import Any

BCP_RTC_EVENTS: tuple[dict[str, Any], ...] = (
    {
        "event_type": "BCP_PACKET_CREATED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "BCP_PACKET_VALIDATED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "BCP_BOOT_REASON_RECORDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "BCP_GOAL_SEED_RECORDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "BCP_AUTHORITY_POSTURE_RECORDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "BCP_ENVIRONMENT_BOUND",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "BCP_PACKET_EXPIRED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "BCP_PACKET_REFUSED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "BCP_SIGNAL_REFUSED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
)


def planned_rtc_events() -> tuple[dict[str, Any], ...]:
    return BCP_RTC_EVENTS


__all__ = ["BCP_RTC_EVENTS", "planned_rtc_events"]
