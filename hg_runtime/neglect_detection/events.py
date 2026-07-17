"""NEG planned RTC event refs — no authority fields."""

from __future__ import annotations

from typing import Any

NEG_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "NEG_NEGLECT_OBSERVED", "authority_fields": False},
    {"event_type": "NEG_REPEAT_MISS_DETECTED", "authority_fields": False},
    {"event_type": "NEG_OVERDUE_REVIEW_DETECTED", "authority_fields": False},
    {"event_type": "NEG_UNROUTED_WARNING_DETECTED", "authority_fields": False},
    {"event_type": "NEG_REVIEW_RECOMMENDED", "authority_fields": False},
    {"event_type": "NEG_SURVEILLANCE_RISK_CONTAINED", "authority_fields": False},
    {"event_type": "NEG_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_neg_event_refs() -> tuple[dict[str, Any], ...]:
    return NEG_EVENT_REFS


__all__ = ["NEG_EVENT_REFS", "planned_neg_event_refs"]
