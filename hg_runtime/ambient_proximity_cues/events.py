"""APC planned event references — observation/containment only."""

from __future__ import annotations

from typing import Any

APC_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "APC_CUE_RECORDED", "authority_fields": False},
    {"event_type": "APC_PROXIMITY_CUE_RECORDED", "authority_fields": False},
    {"event_type": "APC_ATTENTION_DIRECTION_RECORDED", "authority_fields": False},
    {"event_type": "APC_AMBIGUITY_RECORDED", "authority_fields": False},
    {"event_type": "APC_CUE_AS_TRUTH_CONTAINED", "authority_fields": False},
    {"event_type": "APC_CUE_AS_CONSENT_CONTAINED", "authority_fields": False},
    {"event_type": "APC_EMOTION_DIAGNOSIS_CONTAINED", "authority_fields": False},
    {"event_type": "APC_STALE_CUE_REFUSED", "authority_fields": False},
    {"event_type": "APC_CUE_AUTHORITY_CONVERSION_CONTAINED", "authority_fields": False},
    {"event_type": "APC_OPERATOR_REVIEW_RECOMMENDED", "authority_fields": False},
    {"event_type": "APC_CUE_REFUSED", "authority_fields": False},
)


def planned_apc_event_refs() -> tuple[dict[str, Any], ...]:
    return APC_EVENT_REFS


__all__ = ["APC_EVENT_REFS", "planned_apc_event_refs"]
