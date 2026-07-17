"""SBS planned event references — observation/containment only."""

from __future__ import annotations

from typing import Any

SBS_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "SBS_SIGNAL_EMITTED", "authority_fields": False},
    {"event_type": "SBS_SIGNAL_RECEIVED", "authority_fields": False},
    {"event_type": "SBS_SIGNAL_EXPIRED", "authority_fields": False},
    {"event_type": "SBS_CALL_RECORDED", "authority_fields": False},
    {"event_type": "SBS_RESPONSE_RECORDED", "authority_fields": False},
    {"event_type": "SBS_RESONANCE_ASSESSED", "authority_fields": False},
    {"event_type": "SBS_CONTEXT_DISTANCE_RECORDED", "authority_fields": False},
    {"event_type": "SBS_SIGNAL_SATURATION_DETECTED", "authority_fields": False},
    {"event_type": "SBS_SIGNAL_OSCILLATION_DETECTED", "authority_fields": False},
    {"event_type": "SBS_GROUP_STATE_RECORDED", "authority_fields": False},
    {"event_type": "SBS_INCOMPATIBLE_SIGNAL_REFUSED", "authority_fields": False},
    {"event_type": "SBS_SIGNAL_AUTHORITY_CONVERSION_CONTAINED", "authority_fields": False},
    {"event_type": "SBS_OPERATOR_REVIEW_RECOMMENDED", "authority_fields": False},
    {"event_type": "SBS_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_sbs_event_refs() -> tuple[dict[str, Any], ...]:
    return SBS_EVENT_REFS


__all__ = ["SBS_EVENT_REFS", "planned_sbs_event_refs"]
