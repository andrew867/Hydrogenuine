"""PRO planned RTC event design — first safe slice, no emission."""

from __future__ import annotations

from typing import Any

PRO_RTC_EVENTS: tuple[dict[str, Any], ...] = (
    {
        "event_type": "PRO_BODY_STATE_RECORDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PRO_SENSOR_STATE_RECORDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PRO_ACTUATOR_INVENTORY_RECORDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PRO_REACHABLE_ZONE_RECORDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PRO_FORBIDDEN_ZONE_RECORDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PRO_CONTACT_STATE_RECORDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PRO_UNCERTAINTY_RECORDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PRO_ACTUATION_AUTHORITY_CONTAINED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PRO_SIGNAL_REFUSED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
)


def planned_rtc_events() -> tuple[dict[str, Any], ...]:
    return PRO_RTC_EVENTS


__all__ = ["PRO_RTC_EVENTS", "planned_rtc_events"]
