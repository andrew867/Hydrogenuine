"""REB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.reb_cluster.rtc_design import reb_rtc_event

REB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    reb_rtc_event("REB_DISCONTINUITY_EVENT_RECORDED"),
    reb_rtc_event("REB_REENTRY_REQUEST_RECORDED"),
    reb_rtc_event("REB_TEMPORAL_CONTINUITY_ASSESSMENT_CREATED"),
    reb_rtc_event("REB_LONG_GAP_POLICY_APPLIED"),
    reb_rtc_event("REB_REENTRY_DECISION_RECORDED"),
    reb_rtc_event("REB_REENTRY_PACKET_CREATED"),
    reb_rtc_event("REB_REENTRY_ALLOWED_OBSERVE_ONLY"),
    reb_rtc_event("REB_REENTRY_ALLOWED_WITH_DISCLOSURE"),
    reb_rtc_event("REB_REENTRY_REQUIRES_OPERATOR_REVIEW"),
    reb_rtc_event("REB_REENTRY_REQUIRES_TIM_REFRESH"),
    reb_rtc_event("REB_REENTRY_REQUIRES_CNT_REVIEW"),
    reb_rtc_event("REB_REENTRY_DENIED"),
    reb_rtc_event("REB_STALE_APPROVAL_REFUSED"),
    reb_rtc_event("REB_STALE_MEMORY_REFUSED_AS_CURRENT"),
    reb_rtc_event("REB_CHECKPOINT_AUTHORITY_REFUSED"),
    reb_rtc_event("REB_CONTINUITY_CLAIM_REFUSED"),
    reb_rtc_event("REB_AUTHORITY_CONVERSION_CONTAINED"),
    reb_rtc_event("REB_SIGNAL_REFUSED"),
)


def planned_reb_event_refs() -> tuple[dict[str, Any], ...]:
    return REB_EVENT_REFS


__all__ = ["REB_EVENT_REFS", "planned_reb_event_refs"]
