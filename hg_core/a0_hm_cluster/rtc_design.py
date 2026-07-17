"""A0-HM cluster planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

A0_HM_RTC_FAMILY = "agent_zero_heart_mind"

_REQUIRED_RTC_FIELDS = (
    "event_type",
    "family",
    "cognition_eligible",
    "authority_fields",
    "redacted",
    "hashable",
)


def a0_hm_rtc_event(event_type: str) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "family": A0_HM_RTC_FAMILY,
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    }


def is_a0_hm_rtc_event_design(event: dict[str, Any]) -> bool:
    if not all(field in event for field in _REQUIRED_RTC_FIELDS):
        return False
    if event.get("family") != A0_HM_RTC_FAMILY:
        return False
    if event.get("authority_fields") is not False:
        return False
    if event.get("cognition_eligible") is not False:
        return False
    if event.get("redacted") is not True:
        return False
    if event.get("hashable") is not True:
        return False
    return bool(event.get("event_type"))


def validate_a0_hm_rtc_event_design(events: tuple[dict[str, Any], ...]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for index, event in enumerate(events):
        if not is_a0_hm_rtc_event_design(event):
            failures.append(f"event[{index}]={event.get('event_type', '?')}")
    return not failures, failures


__all__ = [
    "A0_HM_RTC_FAMILY",
    "a0_hm_rtc_event",
    "is_a0_hm_rtc_event_design",
    "validate_a0_hm_rtc_event_design",
]
