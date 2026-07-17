"""RXL planned event references — observation/proposal only."""

from __future__ import annotations

from typing import Any

RXL_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "RXL_RECIPROCITY_SIGNAL_RECEIVED", "authority_fields": False},
    {"event_type": "RXL_EXCHANGE_OBSERVED", "authority_fields": False},
    {"event_type": "RXL_RELATIONSHIP_BALANCE_UPDATED", "authority_fields": False},
    {"event_type": "RXL_POSITIVE_FEEDBACK_DETECTED", "authority_fields": False},
    {"event_type": "RXL_NEGATIVE_FEEDBACK_DETECTED", "authority_fields": False},
    {"event_type": "RXL_OSCILLATION_DETECTED", "authority_fields": False},
    {"event_type": "RXL_SATURATION_DETECTED", "authority_fields": False},
    {"event_type": "RXL_ENTITLEMENT_RISK_DETECTED", "authority_fields": False},
    {"event_type": "RXL_DAMPENING_RECOMMENDED", "authority_fields": False},
    {"event_type": "RXL_SIGNAL_EXPIRED", "authority_fields": False},
    {"event_type": "RXL_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_rxl_event_refs() -> tuple[dict[str, Any], ...]:
    return RXL_EVENT_REFS


__all__ = ["RXL_EVENT_REFS", "planned_rxl_event_refs"]
