"""IMS cluster planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

IMS_RTC_FAMILY = "inference_model_scheduler"

_REQUIRED_RTC_FIELDS = (
    "event_type",
    "family",
    "cognition_eligible",
    "authority_fields",
    "redacted",
    "hashable",
)


def ims_rtc_event(event_type: str) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "family": IMS_RTC_FAMILY,
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    }


def is_ims_rtc_event_design(event: dict[str, Any]) -> bool:
    if not all(field in event for field in _REQUIRED_RTC_FIELDS):
        return False
    if event.get("family") != IMS_RTC_FAMILY:
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


def validate_ims_rtc_event_design(events: tuple[dict[str, Any], ...]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for index, event in enumerate(events):
        if not is_ims_rtc_event_design(event):
            failures.append(f"event[{index}]={event.get('event_type', '?')}")
    return not failures, failures


__all__ = [
    "IMS_RTC_FAMILY",
    "is_ims_rtc_event_design",
    "validate_ims_rtc_event_design",
    "ims_rtc_event",
]
