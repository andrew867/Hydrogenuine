"""IIL planned event references — observation only."""

from __future__ import annotations

from typing import Any

IIL_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "IIL_IMPACT_ASSESSMENT_REQUESTED", "authority_fields": False},
    {"event_type": "IIL_IMPACT_ASSESSMENT_RECORDED", "authority_fields": False},
    {"event_type": "IIL_AFFECTED_DOMAIN_IDENTIFIED", "authority_fields": False},
    {"event_type": "IIL_DOWNSTREAM_EFFECT_RECORDED", "authority_fields": False},
    {"event_type": "IIL_BLAST_RADIUS_CLASSIFIED", "authority_fields": False},
    {"event_type": "IIL_EXTERNALITY_CLASSIFIED", "authority_fields": False},
    {"event_type": "IIL_LOCAL_SUCCESS_EXTERNALITY_DETECTED", "authority_fields": False},
    {"event_type": "IIL_CASCADING_EFFECT_DETECTED", "authority_fields": False},
    {"event_type": "IIL_IRREVERSIBLE_IMPACT_DETECTED", "authority_fields": False},
    {"event_type": "IIL_UNKNOWN_IMPACT_GUARDED", "authority_fields": False},
    {"event_type": "IIL_MITIGATION_RECOMMENDED", "authority_fields": False},
    {"event_type": "IIL_OPERATOR_REVIEW_RECOMMENDED", "authority_fields": False},
    {"event_type": "IIL_IMPACT_OBSERVED", "authority_fields": False},
    {"event_type": "IIL_PREDICTION_MISMATCH_DETECTED", "authority_fields": False},
    {"event_type": "IIL_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_iil_event_refs() -> tuple[dict[str, Any], ...]:
    return IIL_EVENT_REFS


__all__ = ["IIL_EVENT_REFS", "planned_iil_event_refs"]
