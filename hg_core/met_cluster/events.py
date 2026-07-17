"""MET cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.met_cluster.rtc_design import met_rtc_event

MET_EVENT_REFS: tuple[dict[str, Any], ...] = (
    met_rtc_event("MET_ENERGY_STATE_OBSERVED"),
    met_rtc_event("MET_INTAKE_REQUESTED"),
    met_rtc_event("MET_INTAKE_QUARANTINED"),
    met_rtc_event("MET_DIGESTION_PROPOSED"),
    met_rtc_event("MET_ASSIMILATION_PROPOSED"),
    met_rtc_event("MET_WASTE_IDENTIFIED"),
    met_rtc_event("MET_DISPOSAL_PROPOSED"),
    met_rtc_event("MET_TOOL_RETIREMENT_PROPOSED"),
    met_rtc_event("MET_DECOMMISSIONING_RECORDED"),
    met_rtc_event("MET_GROWTH_REQUESTED"),
    met_rtc_event("MET_AUTHORITY_CONVERSION_REFUSED"),
    met_rtc_event("MET_FAILED_CLOSED"),
    met_rtc_event("MET_POSTURE_CREATED"),
    met_rtc_event("MET_RECEIPT_CREATED"),
    met_rtc_event("MET_ORGAN_ROUTE_CREATED"),
    met_rtc_event("MET_METABOLIC_SUMMARY_RECORDED"),
)


def planned_met_event_refs() -> tuple[dict[str, Any], ...]:
    return MET_EVENT_REFS


__all__ = ["MET_EVENT_REFS", "planned_met_event_refs"]
