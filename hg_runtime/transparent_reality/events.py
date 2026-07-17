"""TRL planned event references — observation/containment only."""

from __future__ import annotations

from typing import Any

TRL_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "TRL_FIELD_SNAPSHOT_REQUESTED", "authority_fields": False},
    {"event_type": "TRL_FIELD_SNAPSHOT_RECORDED", "authority_fields": False},
    {"event_type": "TRL_EVIDENCE_STATUS_CLASSIFIED", "authority_fields": False},
    {"event_type": "TRL_UNKNOWN_RECORDED", "authority_fields": False},
    {"event_type": "TRL_CONTRADICTION_RECORDED", "authority_fields": False},
    {"event_type": "TRL_STALE_EVIDENCE_RECORDED", "authority_fields": False},
    {"event_type": "TRL_TRANSPARENT_SUMMARY_RECORDED", "authority_fields": False},
    {"event_type": "TRL_NARRATIVE_COLLAPSE_DETECTED", "authority_fields": False},
    {"event_type": "TRL_SUMMARY_AS_PROOF_CONTAINED", "authority_fields": False},
    {"event_type": "TRL_INTEGRATION_AS_AUTHORITY_CONTAINED", "authority_fields": False},
    {"event_type": "TRL_UNKNOWN_ERASURE_DETECTED", "authority_fields": False},
    {"event_type": "TRL_CONTRADICTION_SMOOTHING_DETECTED", "authority_fields": False},
    {"event_type": "TRL_FALSE_OMNISCIENCE_DETECTED", "authority_fields": False},
    {"event_type": "TRL_OPERATOR_REPLACEMENT_CLAIM_CONTAINED", "authority_fields": False},
    {"event_type": "TRL_OPERATOR_REVIEW_RECOMMENDED", "authority_fields": False},
    {"event_type": "TRL_OBT_GATE_RECOMMENDED", "authority_fields": False},
    {"event_type": "TRL_SAFE_MODE_RECOMMENDED", "authority_fields": False},
    {"event_type": "TRL_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_trl_event_refs() -> tuple[dict[str, Any], ...]:
    return TRL_EVENT_REFS


__all__ = ["TRL_EVENT_REFS", "planned_trl_event_refs"]
