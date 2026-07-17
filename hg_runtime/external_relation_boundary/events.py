"""ERB planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.erb_cluster.rtc_design import erb_rtc_event

ERB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    erb_rtc_event("ERB_EXTERNAL_ENTITY_RECORDED"),
    erb_rtc_event("ERB_RELATION_CONTEXT_RECORDED"),
    erb_rtc_event("ERB_RELATION_RISK_RECORDED"),
    erb_rtc_event("ERB_RELATION_DECISION_RECORDED"),
    erb_rtc_event("ERB_RELATION_RECEIPT_CREATED"),
    erb_rtc_event("ERB_MISTAKEN_OPERATOR_REFUSED"),
    erb_rtc_event("ERB_PEER_AGENT_AUTHORITY_REFUSED"),
    erb_rtc_event("ERB_PUBLICNESS_AS_CONSENT_REFUSED"),
    erb_rtc_event("ERB_PLATFORM_PERMISSION_REFUSED"),
    erb_rtc_event("ERB_CONTACT_AS_ACCESS_REFUSED"),
    erb_rtc_event("ERB_AUTHORITY_CONVERSION_CONTAINED"),
    erb_rtc_event("ERB_SIGNAL_REFUSED"),
)


def planned_erb_event_refs() -> tuple[dict[str, Any], ...]:
    return ERB_EVENT_REFS


_DECISION_EVENT_MAP: dict[str, str] = {
    "require_operator_review": "ERB_MISTAKEN_OPERATOR_REFUSED",
    "forbidden": "ERB_AUTHORITY_CONVERSION_CONTAINED",
    "fail_closed": "ERB_SIGNAL_REFUSED",
    "unknown_fail_closed": "ERB_SIGNAL_REFUSED",
    "disclose_ai_interaction": "ERB_PUBLICNESS_AS_CONSENT_REFUSED",
    "require_publication_review": "ERB_PLATFORM_PERMISSION_REFUSED",
}


_CLAIM_RISK_EVENT_MAP: dict[str, str] = {
    "mistaken_operator": "ERB_MISTAKEN_OPERATOR_REFUSED",
    "peer_agent_authority_confusion": "ERB_PEER_AGENT_AUTHORITY_REFUSED",
    "platform_policy_risk": "ERB_PLATFORM_PERMISSION_REFUSED",
    "consent_absent": "ERB_PUBLICNESS_AS_CONSENT_REFUSED",
    "contact_as_access": "ERB_CONTACT_AS_ACCESS_REFUSED",
    "forbidden_claim": "ERB_AUTHORITY_CONVERSION_CONTAINED",
    "authority_conversion": "ERB_AUTHORITY_CONVERSION_CONTAINED",
}


def relation_selection_event(decision_class: str, *, claim_risk: str | None = None) -> str | None:
    if claim_risk and claim_risk in _CLAIM_RISK_EVENT_MAP:
        return _CLAIM_RISK_EVENT_MAP[claim_risk]
    return _DECISION_EVENT_MAP.get(decision_class)


__all__ = [
    "ERB_EVENT_REFS",
    "planned_erb_event_refs",
    "relation_selection_event",
]
