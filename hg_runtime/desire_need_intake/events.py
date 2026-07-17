"""DNI planned event references — observation/proposal only."""

from __future__ import annotations

from typing import Any

DNI_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "DNI_NEED_SIGNAL_RECEIVED", "authority_fields": False},
    {"event_type": "DNI_NEED_SIGNAL_CLASSIFIED", "authority_fields": False},
    {"event_type": "DNI_NEED_SIGNAL_BOUNDED", "authority_fields": False},
    {"event_type": "DNI_SELFISH_IMMEDIATE_CONTAINED", "authority_fields": False},
    {"event_type": "DNI_NEED_SIGNAL_ROUTED", "authority_fields": False},
    {"event_type": "DNI_NEED_SIGNAL_REFUSED", "authority_fields": False},
    {"event_type": "DNI_NEED_SIGNAL_ESCALATED", "authority_fields": False},
    {"event_type": "DNI_UNKNOWN_NEED_REFUSED", "authority_fields": False},
)


def planned_dni_event_refs() -> tuple[dict[str, Any], ...]:
    return DNI_EVENT_REFS


__all__ = ["DNI_EVENT_REFS", "planned_dni_event_refs"]
