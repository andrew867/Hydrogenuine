"""SIM planned RTC event design — first safe slice, no emission."""

from __future__ import annotations

from typing import Any

SIM_RTC_EVENTS: tuple[dict[str, Any], ...] = (
    {
        "event_type": "SIM_SCENARIO_CREATED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "SIM_ASSUMPTION_RECORDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "SIM_OUTCOME_PREDICTED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "SIM_UNCERTAINTY_RECORDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "SIM_FORBIDDEN_ACTION_DETECTED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "SIM_REHEARSAL_COMPLETED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "SIM_REHEARSAL_REFUSED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "SIM_SIGNAL_REFUSED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
)


def planned_rtc_events() -> tuple[dict[str, Any], ...]:
    return SIM_RTC_EVENTS


__all__ = ["SIM_RTC_EVENTS", "planned_rtc_events"]
