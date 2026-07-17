"""H8 cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.h8_cluster.rtc_design import h8_rtc_event

H8_EVENT_REFS: tuple[dict[str, Any], ...] = (
    h8_rtc_event("H8_ORGANISM_STATE_SUMMARY_CREATED"),
    h8_rtc_event("H8_COHERENCE_RECEIPT_CREATED"),
    h8_rtc_event("H8_CONFLICT_ROUTED"),
    h8_rtc_event("H8_ORGANISM_COHERENCE_RECORDED"),
    h8_rtc_event("H8_MISSING_ORGAN_FAILED_CLOSED"),
    h8_rtc_event("H8_STALE_APPROVAL_FAILED_CLOSED"),
    h8_rtc_event("H8_NAKED_SCALAR_REFUSED"),
    h8_rtc_event("H8_DRB_FRAGMENT_AS_PERMISSION_REFUSED"),
    h8_rtc_event("H8_TEP_ENVELOPE_AS_AUTHORITY_REFUSED"),
    h8_rtc_event("H8_A0_HM_POSTURE_AS_AUTHORITY_REFUSED"),
    h8_rtc_event("H8_BOUNDARY_CHAIN_AUTHORITY_REFUSED"),
    h8_rtc_event("H8_AUTHORITY_CONVERSION_CONTAINED"),
    h8_rtc_event("H8_UNKNOWN_ORGANISM_FAILED_CLOSED"),
)


def planned_h8_event_refs() -> tuple[dict[str, Any], ...]:
    return H8_EVENT_REFS


__all__ = ["H8_EVENT_REFS", "planned_h8_event_refs"]
