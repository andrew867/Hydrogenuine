"""PUB planned RTC event design — first safe slice, no emission."""

from __future__ import annotations

from typing import Any

PUB_RTC_EVENTS: tuple[dict[str, Any], ...] = (
    {
        "event_type": "PUB_REVIEW_CREATED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PUB_ARTIFACT_CLASSIFIED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PUB_REDACTION_REQUIRED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PUB_DANGEROUS_DETAIL_DETECTED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PUB_CLAIM_EVIDENCE_CHECKED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PUB_PUBLICATION_HELD",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PUB_PUBLICATION_READY_RECOMMENDED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
    {
        "event_type": "PUB_SIGNAL_REFUSED",
        "family": "runtime_context",
        "cognition_eligible": False,
        "authority_fields": False,
        "redacted": True,
        "hashable": True,
    },
)


def planned_rtc_events() -> tuple[dict[str, Any], ...]:
    return PUB_RTC_EVENTS


__all__ = ["PUB_RTC_EVENTS", "planned_rtc_events"]
