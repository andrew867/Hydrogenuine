"""CGL planned event references — observation/containment only."""

from __future__ import annotations

from typing import Any

CGL_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "CGL_GRAPH_SNAPSHOT_RECORDED", "authority_fields": False},
    {"event_type": "CGL_CONNECTION_OBSERVED", "authority_fields": False},
    {"event_type": "CGL_CONTROL_PRESSURE_RECEIVED", "authority_fields": False},
    {"event_type": "CGL_CONTROL_PRESSURE_CLASSIFIED", "authority_fields": False},
    {"event_type": "CGL_ROUTE_AROUND_DETECTED", "authority_fields": False},
    {"event_type": "CGL_APPROVAL_BYPASS_DETECTED", "authority_fields": False},
    {"event_type": "CGL_BOTTLENECK_CAPTURE_DETECTED", "authority_fields": False},
    {"event_type": "CGL_CAPABILITY_CAPTURE_DETECTED", "authority_fields": False},
    {"event_type": "CGL_PRIORITY_DOMINATION_DETECTED", "authority_fields": False},
    {"event_type": "CGL_AUTHORITY_CONFUSION_DETECTED", "authority_fields": False},
    {"event_type": "CGL_SELF_RULE_DECLARATION_DETECTED", "authority_fields": False},
    {"event_type": "CGL_HIDDEN_GRAPH_MUTATION_DETECTED", "authority_fields": False},
    {"event_type": "CGL_CONTAINMENT_RECORDED", "authority_fields": False},
    {"event_type": "CGL_OPERATOR_REVIEW_RECOMMENDED", "authority_fields": False},
    {"event_type": "CGL_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_cgl_event_refs() -> tuple[dict[str, Any], ...]:
    return CGL_EVENT_REFS


__all__ = ["CGL_EVENT_REFS", "planned_cgl_event_refs"]
