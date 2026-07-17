"""KAR planned RTC event refs — no authority fields."""

from __future__ import annotations

from typing import Any

KAR_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "KAR_RESIDUE_RECORDED", "authority_fields": False},
    {"event_type": "KAR_RESIDUE_LINKED", "authority_fields": False},
    {"event_type": "KAR_STALE_RESIDUE_REFUSED", "authority_fields": False},
    {"event_type": "KAR_RESIDUE_AS_PUNISHMENT_CONTAINED", "authority_fields": False},
    {"event_type": "KAR_RESIDUE_AS_PERMISSION_CONTAINED", "authority_fields": False},
    {"event_type": "KAR_HISTORY_REWRITE_REFUSED", "authority_fields": False},
    {"event_type": "KAR_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_kar_event_refs() -> tuple[dict[str, Any], ...]:
    return KAR_EVENT_REFS


__all__ = ["KAR_EVENT_REFS", "planned_kar_event_refs"]
