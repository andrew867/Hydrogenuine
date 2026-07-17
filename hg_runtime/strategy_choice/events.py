"""SCL planned event references — observation/proposal only."""

from __future__ import annotations

from typing import Any

SCL_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "SCL_STRATEGY_CONTEXT_RECEIVED", "authority_fields": False},
    {"event_type": "SCL_STRATEGY_OPTIONS_ENUMERATED", "authority_fields": False},
    {"event_type": "SCL_STRATEGY_OPTION_SCORED", "authority_fields": False},
    {"event_type": "SCL_STRATEGY_BLOCKED", "authority_fields": False},
    {"event_type": "SCL_STRATEGY_SELECTED", "authority_fields": False},
    {"event_type": "SCL_STRATEGY_SELECTION_REFUSED", "authority_fields": False},
    {"event_type": "SCL_TRADEOFF_RECORDED", "authority_fields": False},
    {"event_type": "SCL_CONSEQUENCE_PREDICTED", "authority_fields": False},
    {"event_type": "SCL_CONSEQUENCE_OBSERVED", "authority_fields": False},
    {"event_type": "SCL_OUTCOME_MATCHED", "authority_fields": False},
    {"event_type": "SCL_OUTCOME_MISMATCH_DETECTED", "authority_fields": False},
    {"event_type": "SCL_RESPONSIBILITY_RECORDED", "authority_fields": False},
    {"event_type": "SCL_OPERATOR_REVIEW_RECOMMENDED", "authority_fields": False},
    {"event_type": "SCL_TRUTH_GATE_RECOMMENDED", "authority_fields": False},
    {"event_type": "SCL_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_scl_event_refs() -> tuple[dict[str, Any], ...]:
    return SCL_EVENT_REFS


__all__ = ["SCL_EVENT_REFS", "planned_scl_event_refs"]
