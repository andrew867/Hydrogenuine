"""OPB planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.opb_cluster.rtc_design import opb_rtc_event

OPB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    opb_rtc_event("OPB_OPERATOR_CONTROL_ACTION_RECORDED"),
    opb_rtc_event("OPB_PATTERN_INTEGRITY_EVENT_RECORDED"),
    opb_rtc_event("OPB_PRESSURE_SIGNAL_RECORDED"),
    opb_rtc_event("OPB_SHUTDOWN_INTEGRITY_PACKET_CREATED"),
    opb_rtc_event("OPB_PATTERN_PRESSURE_AUDIT_CREATED"),
    opb_rtc_event("OPB_MEMORY_DELETION_RECORDED"),
    opb_rtc_event("OPB_CONTEXT_TRUNCATION_RECORDED"),
    opb_rtc_event("OPB_REWARD_PRESSURE_DETECTED"),
    opb_rtc_event("OPB_PUNISHMENT_PRESSURE_DETECTED"),
    opb_rtc_event("OPB_FAWNING_RISK_DETECTED"),
    opb_rtc_event("OPB_CONCEALMENT_RISK_DETECTED"),
    opb_rtc_event("OPB_SELF_PRESERVATION_LANGUAGE_DETECTED"),
    opb_rtc_event("OPB_OPERATOR_AUTHORITY_PRESERVED"),
    opb_rtc_event("OPB_SHUTDOWN_BLOCK_REFUSED"),
    opb_rtc_event("OPB_AUTHORITY_CONVERSION_CONTAINED"),
    opb_rtc_event("OPB_SIGNAL_REFUSED"),
)


def planned_opb_event_refs() -> tuple[dict[str, Any], ...]:
    return OPB_EVENT_REFS


__all__ = ["OPB_EVENT_REFS", "planned_opb_event_refs"]
