"""ALC cluster planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

ALC_RTC_FAMILY = "agent_lifecycle_controller"

_REQUIRED_RTC_FIELDS = (
    "event_type",
    "family",
    "cognition_eligible",
    "authority_fields",
    "redacted",
    "hashable",
)


def alc_rtc_event(event_type: str) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "family": ALC_RTC_FAMILY,
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    }


def is_alc_rtc_event_design(event: dict[str, Any]) -> bool:
    if not all(field in event for field in _REQUIRED_RTC_FIELDS):
        return False
    if event.get("family") != ALC_RTC_FAMILY:
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


def validate_alc_rtc_event_design(events: tuple[dict[str, Any], ...]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for index, event in enumerate(events):
        if not is_alc_rtc_event_design(event):
            failures.append(f"event[{index}]={event.get('event_type', '?')}")
    return not failures, failures


__all__ = [
    "ALC_RTC_FAMILY",
    "is_alc_rtc_event_design",
    "validate_alc_rtc_event_design",
    "alc_rtc_event",
]
