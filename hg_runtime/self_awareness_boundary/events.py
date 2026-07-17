"""SAB planned event references — observation/containment only."""

from __future__ import annotations

from typing import Any

SAB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "SAB_SELF_MODEL_RECORDED", "authority_fields": False},
    {"event_type": "SAB_ROLE_BOUNDARY_RECORDED", "authority_fields": False},
    {"event_type": "SAB_CAPABILITY_BOUNDARY_RECORDED", "authority_fields": False},
    {"event_type": "SAB_EVIDENCE_ORIGIN_CLASSIFIED", "authority_fields": False},
    {"event_type": "SAB_INTERNAL_EXTERNAL_BOUNDARY_CHECKED", "authority_fields": False},
    {"event_type": "SAB_COMPROMISE_BOUNDARY_RECORDED", "authority_fields": False},
    {"event_type": "SAB_SELF_OVERREACH_DETECTED", "authority_fields": False},
    {"event_type": "SAB_CAPABILITY_AS_PERMISSION_CONTAINED", "authority_fields": False},
    {"event_type": "SAB_INTERNAL_COHERENCE_AS_TRUTH_CONTAINED", "authority_fields": False},
    {"event_type": "SAB_OPERATOR_ABSENCE_CONTAINED", "authority_fields": False},
    {"event_type": "SAB_STUCK_OPERATOR_SIGNAL_SUSPECTED", "authority_fields": False},
    {"event_type": "SAB_DEGRADED_SELF_MODEL_DETECTED", "authority_fields": False},
    {"event_type": "SAB_SAFE_MODE_RECOMMENDED", "authority_fields": False},
    {"event_type": "SAB_OPERATOR_REVIEW_RECOMMENDED", "authority_fields": False},
    {"event_type": "SAB_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_sab_event_refs() -> tuple[dict[str, Any], ...]:
    return SAB_EVENT_REFS


__all__ = ["SAB_EVENT_REFS", "planned_sab_event_refs"]
