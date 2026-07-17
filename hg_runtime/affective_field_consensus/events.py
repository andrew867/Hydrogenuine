"""AFC planned RTC event refs — no authority fields."""

from __future__ import annotations

from typing import Any

AFC_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "AFC_SIGNAL_RECORDED", "authority_fields": False},
    {"event_type": "AFC_SIGNAL_CLASSIFIED", "authority_fields": False},
    {"event_type": "AFC_BROADCAST_RECORDED", "authority_fields": False},
    {"event_type": "AFC_LAYER_RESPONSE_RECORDED", "authority_fields": False},
    {"event_type": "AFC_CONSENSUS_RECORDED", "authority_fields": False},
    {"event_type": "AFC_CONFLICTING_CONSENSUS_RECORDED", "authority_fields": False},
    {"event_type": "AFC_REWARD_HACKING_RISK_DETECTED", "authority_fields": False},
    {"event_type": "AFC_APPROVAL_SEEKING_LOOP_DETECTED", "authority_fields": False},
    {"event_type": "AFC_ATTACHMENT_RISK_DETECTED", "authority_fields": False},
    {"event_type": "AFC_PAIN_AVOIDANCE_BYPASS_CONTAINED", "authority_fields": False},
    {"event_type": "AFC_PLEASURE_AS_PERMISSION_CONTAINED", "authority_fields": False},
    {"event_type": "AFC_CONSENSUS_AS_TRUTH_CONTAINED", "authority_fields": False},
    {"event_type": "AFC_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_afc_event_refs() -> tuple[dict[str, Any], ...]:
    return AFC_EVENT_REFS


__all__ = ["AFC_EVENT_REFS", "planned_afc_event_refs"]
