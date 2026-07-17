"""OBL planned RTC event refs — no authority fields."""

from __future__ import annotations

from typing import Any

OBL_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "OBL_OBLIGATION_RECORDED", "authority_fields": False},
    {"event_type": "OBL_OBLIGATION_CLASSIFIED", "authority_fields": False},
    {"event_type": "OBL_CLEANUP_RECOMMENDED", "authority_fields": False},
    {"event_type": "OBL_DISCLOSURE_RECOMMENDED", "authority_fields": False},
    {"event_type": "OBL_COMPENSATION_RECOMMENDED", "authority_fields": False},
    {"event_type": "OBL_OBLIGATION_CLOSED", "authority_fields": False},
    {"event_type": "OBL_OVERDUE_DETECTED", "authority_fields": False},
    {"event_type": "OBL_AUTHORITY_CONVERSION_CONTAINED", "authority_fields": False},
    {"event_type": "OBL_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_obl_event_refs() -> tuple[dict[str, Any], ...]:
    return OBL_EVENT_REFS


__all__ = ["OBL_EVENT_REFS", "planned_obl_event_refs"]
