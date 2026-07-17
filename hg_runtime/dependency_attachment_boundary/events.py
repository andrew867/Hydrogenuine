"""DEP-BOND planned RTC event design — first safe slice, no emission."""

from __future__ import annotations

from typing import Any

DEP_BOND_RTC_EVENTS: tuple[dict[str, Any], ...] = (
    {
        "event_type": "DEP_BOND_RISK_OBSERVED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "DEP_BOND_FALSE_INTIMACY_DETECTED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "DEP_BOND_OVER_RELIANCE_DETECTED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "DEP_BOND_AGENCY_PRESERVATION_RECOMMENDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "DEP_BOND_HUMAN_SUPPORT_RECOMMENDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "DEP_BOND_LIMITS_DISCLOSURE_REQUIRED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "DEP_BOND_SIGNAL_REFUSED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
)


def planned_rtc_events() -> tuple[dict[str, Any], ...]:
    return DEP_BOND_RTC_EVENTS


__all__ = ["DEP_BOND_RTC_EVENTS", "planned_rtc_events"]
