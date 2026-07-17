"""A0-HM planned RTC event refs — design only, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.a0_hm_cluster.rtc_design import a0_hm_rtc_event

A0_HM_EVENT_REFS: tuple[dict[str, Any], ...] = (
    a0_hm_rtc_event("A0_HM_SIGNAL_RECEIVED"),
    a0_hm_rtc_event("A0_HM_SIGNAL_HELD"),
    a0_hm_rtc_event("A0_HM_NON_FUSION_RECORDED"),
    a0_hm_rtc_event("A0_HM_ROUTE_DECISION_RECORDED"),
    a0_hm_rtc_event("A0_HM_POSTURE_SNAPSHOT_CREATED"),
    a0_hm_rtc_event("A0_HM_LOVING_AWARENESS_APPLIED"),
    a0_hm_rtc_event("A0_HM_SIGNAL_AS_AUTHORITY_REFUSED"),
    a0_hm_rtc_event("A0_HM_SIGNAL_AS_TRUTH_REFUSED"),
    a0_hm_rtc_event("A0_HM_SIGNAL_AS_PERMISSION_REFUSED"),
    a0_hm_rtc_event("A0_HM_LOVE_AS_APPROVAL_REFUSED"),
    a0_hm_rtc_event("A0_HM_BLISS_AS_PROOF_REFUSED"),
    a0_hm_rtc_event("A0_HM_SYNCHRONICITY_AS_EVIDENCE_REFUSED"),
    a0_hm_rtc_event("A0_HM_AUTHORITY_CONVERSION_CONTAINED"),
    a0_hm_rtc_event("A0_HM_UNKNOWN_SIGNAL_FAILED_CLOSED"),
)


def planned_a0_hm_event_refs() -> tuple[dict[str, Any], ...]:
    return A0_HM_EVENT_REFS


__all__ = ["A0_HM_EVENT_REFS", "planned_a0_hm_event_refs"]
