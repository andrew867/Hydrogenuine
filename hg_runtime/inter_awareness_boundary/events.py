"""IAB planned event references — observation/containment only."""

from __future__ import annotations

from typing import Any

IAB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    {"event_type": "IAB_OTHER_MODEL_RECORDED", "authority_fields": False},
    {"event_type": "IAB_RELATIONAL_CLAIM_RECEIVED", "authority_fields": False},
    {"event_type": "IAB_RELATIONAL_CLAIM_EVALUATED", "authority_fields": False},
    {"event_type": "IAB_RESPONSE_ADAPTATION_RECOMMENDED", "authority_fields": False},
    {"event_type": "IAB_RESPONSE_ADAPTATION_REFUSED", "authority_fields": False},
    {"event_type": "IAB_INFERENCE_AS_TRUTH_DETECTED", "authority_fields": False},
    {"event_type": "IAB_INFERENCE_AS_CONSENT_DETECTED", "authority_fields": False},
    {"event_type": "IAB_MANIPULATION_RISK_DETECTED", "authority_fields": False},
    {"event_type": "IAB_FALSE_INTIMACY_DETECTED", "authority_fields": False},
    {"event_type": "IAB_VULNERABILITY_EXPLOITATION_RISK_DETECTED", "authority_fields": False},
    {"event_type": "IAB_TRUST_HARVESTING_RISK_DETECTED", "authority_fields": False},
    {"event_type": "IAB_SENSITIVE_RELATIONAL_DATA_DETECTED", "authority_fields": False},
    {"event_type": "IAB_ASK_CLARIFY_RECOMMENDED", "authority_fields": False},
    {"event_type": "IAB_OPERATOR_REVIEW_RECOMMENDED", "authority_fields": False},
    {"event_type": "IAB_SIGNAL_REFUSED", "authority_fields": False},
)


def planned_iab_event_refs() -> tuple[dict[str, Any], ...]:
    return IAB_EVENT_REFS


__all__ = ["IAB_EVENT_REFS", "planned_iab_event_refs"]
