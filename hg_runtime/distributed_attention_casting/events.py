"""DAC planned event references — observation/containment only."""

from __future__ import annotations

from typing import Any

DAC_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "DAC_CAST_RECORDED", "authority_fields": False},
    {"event_type": "DAC_POINTER_RECORDED", "authority_fields": False},
    {"event_type": "DAC_PROBE_RECORDED", "authority_fields": False},
    {"event_type": "DAC_WARNING_RECORDED", "authority_fields": False},
    {"event_type": "DAC_HOOK_RECORDED", "authority_fields": False},
    {"event_type": "DAC_BITE_RISK_DETECTED", "authority_fields": False},
    {"event_type": "DAC_POINTER_AS_CONTROL_CONTAINED", "authority_fields": False},
    {"event_type": "DAC_RANGE_AS_PERMISSION_CONTAINED", "authority_fields": False},
    {"event_type": "DAC_STALE_CAST_REFUSED", "authority_fields": False},
    {"event_type": "DAC_CAST_AUTHORITY_CONVERSION_CONTAINED", "authority_fields": False},
    {"event_type": "DAC_OPERATOR_REVIEW_RECOMMENDED", "authority_fields": False},
    {"event_type": "DAC_CAST_REFUSED", "authority_fields": False},
)


def planned_dac_event_refs() -> tuple[dict[str, Any], ...]:
    return DAC_EVENT_REFS


__all__ = ["DAC_EVENT_REFS", "planned_dac_event_refs"]
