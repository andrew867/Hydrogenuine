"""CRR event references for integration alignment — existing RTC types."""

from __future__ import annotations

from typing import Any

# References event types already registered in event_types_v1.yaml.
CRR_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "CRR_TRIGGER_DECIDED", "authority_fields": False},
    {"event_type": "CRR_RECOVERY_CYCLE_STARTED", "authority_fields": False},
    {"event_type": "CRR_RECOVERY_CYCLE_COMPLETED", "authority_fields": False},
    {"event_type": "CRR_RECOVERY_CYCLE_FAILED", "authority_fields": False},
    {"event_type": "CRR_ADMISSION_PAUSED", "authority_fields": False},
    {"event_type": "CRR_CHECKPOINT_RECORDED", "authority_fields": False},
    {"event_type": "CRR_RECOVERY_ESCALATION_REFUSED", "authority_fields": False},
    {"event_type": "CRR_CYCLE_RECORDED", "authority_fields": False},
)


def planned_crr_event_refs() -> tuple[dict[str, Any], ...]:
    return CRR_EVENT_REFS


__all__ = ["CRR_EVENT_REFS", "planned_crr_event_refs"]
