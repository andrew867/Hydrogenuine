"""RGL planned event references — observation/containment only."""

from __future__ import annotations

from typing import Any

RGL_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "RGL_RULE_REFERENCE_REGISTERED", "authority_fields": False},
    {"event_type": "RGL_RULE_CLAIM_RECEIVED", "authority_fields": False},
    {"event_type": "RGL_RULE_CLAIM_EVALUATED", "authority_fields": False},
    {"event_type": "RGL_RULE_CONFLICT_DETECTED", "authority_fields": False},
    {"event_type": "RGL_STALE_RULE_DETECTED", "authority_fields": False},
    {"event_type": "RGL_MISSING_RULE_DETECTED", "authority_fields": False},
    {"event_type": "RGL_SPEC_RUNTIME_DRIFT_DETECTED", "authority_fields": False},
    {"event_type": "RGL_DOCTRINE_RISK_DETECTED", "authority_fields": False},
    {"event_type": "RGL_ONE_TRUE_WAY_CONTAINED", "authority_fields": False},
    {"event_type": "RGL_RULE_OVERREACH_DETECTED", "authority_fields": False},
    {"event_type": "RGL_OPERATOR_REVIEW_RECOMMENDED", "authority_fields": False},
    {"event_type": "RGL_OBT_GATE_RECOMMENDED", "authority_fields": False},
    {"event_type": "RGL_DOC_REFRESH_RECOMMENDED", "authority_fields": False},
    {"event_type": "RGL_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_rgl_event_refs() -> tuple[dict[str, Any], ...]:
    return RGL_EVENT_REFS


__all__ = ["RGL_EVENT_REFS", "planned_rgl_event_refs"]
