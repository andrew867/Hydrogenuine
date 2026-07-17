"""CNT planned event references — observation/proposal only."""

from __future__ import annotations

from typing import Any

CNT_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "CNT_CONTINUITY_CLAIM_RECORDED", "authority_fields": False},
    {"event_type": "CNT_SUCCESSOR_CLASSIFIED", "authority_fields": False},
    {"event_type": "CNT_FORK_CLASSIFIED", "authority_fields": False},
    {"event_type": "CNT_RESTORE_CLASSIFIED", "authority_fields": False},
    {"event_type": "CNT_IDENTITY_CONTINUITY_REFUSED", "authority_fields": False},
    {"event_type": "CNT_STALE_AUTHORITY_INHERITANCE_CONTAINED", "authority_fields": False},
    {"event_type": "CNT_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_cnt_event_refs() -> tuple[dict[str, Any], ...]:
    return CNT_EVENT_REFS


__all__ = ["CNT_EVENT_REFS", "planned_cnt_event_refs"]
