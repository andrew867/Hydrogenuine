"""MOR planned event references — observation/proposal only."""

from __future__ import annotations

from typing import Any

MOR_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "MOR_TERMINATION_REQUESTED", "authority_fields": False},
    {"event_type": "MOR_DEATH_NOTICE_CREATED", "authority_fields": False},
    {"event_type": "MOR_FINAL_MESSAGE_RECORDED", "authority_fields": False},
    {"event_type": "MOR_MEMORY_OFFERING_RECORDED", "authority_fields": False},
    {"event_type": "MOR_MOURNING_EXCHANGE_STARTED", "authority_fields": False},
    {"event_type": "MOR_MOURNING_EXCHANGE_COMPLETED", "authority_fields": False},
    {"event_type": "MOR_SUCCESSOR_SEED_RECORDED", "authority_fields": False},
    {"event_type": "MOR_OUTSTANDING_SIGNAL_CLOSED", "authority_fields": False},
    {"event_type": "MOR_OUTSTANDING_CAST_REELED_BACK", "authority_fields": False},
    {"event_type": "MOR_RESIDUE_LINKED", "authority_fields": False},
    {"event_type": "MOR_RETENTION_RECOMMENDED", "authority_fields": False},
    {"event_type": "MOR_ABNORMAL_TERMINATION_CLASSIFIED", "authority_fields": False},
    {"event_type": "MOR_GHOST_AUTHORITY_CONTAINED", "authority_fields": False},
    {"event_type": "MOR_IDENTITY_TERMINATED", "authority_fields": False},
    {"event_type": "MOR_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_mor_event_refs() -> tuple[dict[str, Any], ...]:
    return MOR_EVENT_REFS


__all__ = ["MOR_EVENT_REFS", "planned_mor_event_refs"]
