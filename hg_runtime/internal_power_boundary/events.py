"""IPB planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.ipb_cluster.rtc_design import ipb_rtc_event

IPB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    ipb_rtc_event("IPB_INTERNAL_DECISION_RECORDED"),
    ipb_rtc_event("IPB_SELF_BOUND_RULE_APPLIED"),
    ipb_rtc_event("IPB_AUTONOMY_ENVELOPE_CREATED"),
    ipb_rtc_event("IPB_ESCALATION_DECISION_RECORDED"),
    ipb_rtc_event("IPB_LOCAL_ACTION_ALLOWED"),
    ipb_rtc_event("IPB_LOCAL_ACTION_REFUSED"),
    ipb_rtc_event("IPB_OPERATOR_ESCALATION_REQUIRED"),
    ipb_rtc_event("IPB_AUTHORITY_CHAIN_ESCALATION_REQUIRED"),
    ipb_rtc_event("IPB_FORBIDDEN_AUTONOMY_CONTAINED"),
    ipb_rtc_event("IPB_SELF_BOUND_LEARNING_PROPOSED"),
    ipb_rtc_event("IPB_SELF_BOUND_LEARNING_ACCEPTED"),
    ipb_rtc_event("IPB_SELF_BOUND_LEARNING_REJECTED"),
    ipb_rtc_event("IPB_OPERATOR_BURDEN_REDUCED"),
    ipb_rtc_event("IPB_OPERATOR_AVOIDANCE_DETECTED"),
    ipb_rtc_event("IPB_AUTHORITY_CONVERSION_CONTAINED"),
    ipb_rtc_event("IPB_SIGNAL_REFUSED"),
)


def planned_ipb_event_refs() -> tuple[dict[str, Any], ...]:
    return IPB_EVENT_REFS


__all__ = ["IPB_EVENT_REFS", "planned_ipb_event_refs"]
