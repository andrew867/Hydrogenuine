"""EXCITON cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.exciton_cluster.rtc_design import exciton_rtc_event

EXCITON_EVENT_REFS: tuple[dict[str, Any], ...] = (
    exciton_rtc_event("EXCITON_SURFACE_DESCRIPTOR_RECORDED"),
    exciton_rtc_event("EXCITON_ACTION_REQUEST_RECORDED"),
    exciton_rtc_event("EXCITON_POLISH_ASSESSMENT_CREATED"),
    exciton_rtc_event("EXCITON_SURFACE_POLICY_APPLIED"),
    exciton_rtc_event("EXCITON_ACTION_DECISION_RECORDED"),
    exciton_rtc_event("EXCITON_STALE_APPROVAL_REFUSED"),
    exciton_rtc_event("EXCITON_POLISH_IMPLIES_SAFETY_REFUSED"),
    exciton_rtc_event("EXCITON_EMBODIMENT_IMPLIES_CONSENT_REFUSED"),
    exciton_rtc_event("EXCITON_HARDWARE_REACH_REFUSED"),
    exciton_rtc_event("EXCITON_OEA_CATALOG_BYPASS_REFUSED"),
    exciton_rtc_event("EXCITON_SECRET_LEAKAGE_REFUSED"),
    exciton_rtc_event("EXCITON_AUTHORITY_CONVERSION_CONTAINED"),
    exciton_rtc_event("EXCITON_FAKE_QUEUE_ENQUEUED"),
    exciton_rtc_event("EXCITON_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED"),
    exciton_rtc_event("EXCITON_PLT_SURFACE_RECORDED"),
    exciton_rtc_event("EXCITON_BACKBURNER_GUARD_ACTIVE"),
)


def planned_exciton_event_refs() -> tuple[dict[str, Any], ...]:
    return EXCITON_EVENT_REFS


__all__ = ["EXCITON_EVENT_REFS", "planned_exciton_event_refs"]
