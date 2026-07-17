"""DRB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.drb_cluster.rtc_design import drb_rtc_event

DRB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    drb_rtc_event("DRB_REFLECTION_REQUEST_RECORDED"),
    drb_rtc_event("DRB_COUNTERFACTUAL_SCENARIO_CREATED"),
    drb_rtc_event("DRB_DREAM_FRAGMENT_CREATED"),
    drb_rtc_event("DRB_CONSOLIDATION_DECISION_RECORDED"),
    drb_rtc_event("DRB_REFLECTION_RECEIPT_CREATED"),
    drb_rtc_event("DRB_SCENARIO_AS_HISTORY_REFUSED"),
    drb_rtc_event("DRB_FRAGMENT_AS_MEMORY_REFUSED"),
    drb_rtc_event("DRB_SIMULATION_AS_PROOF_REFUSED"),
    drb_rtc_event("DRB_BETTER_OUTCOME_AS_REVISION_REFUSED"),
    drb_rtc_event("DRB_FRAGMENT_AS_AUTHORITY_REFUSED"),
    drb_rtc_event("DRB_AUTHORITY_CONVERSION_CONTAINED"),
    drb_rtc_event("DRB_UNKNOWN_REFLECTION_FAILED_CLOSED"),
)


def planned_drb_event_refs() -> tuple[dict[str, Any], ...]:
    return DRB_EVENT_REFS


__all__ = ["DRB_EVENT_REFS", "planned_drb_event_refs"]
