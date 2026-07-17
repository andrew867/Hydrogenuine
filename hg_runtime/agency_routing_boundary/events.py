"""ARB planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.arb_cluster.rtc_design import arb_rtc_event

ARB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    arb_rtc_event("ARB_AGENT0_SIGNAL_RECORDED"),
    arb_rtc_event("ARB_L1_L9_SIGNAL_RECORDED"),
    arb_rtc_event("ARB_ROUTE_DECISION_RECORDED"),
    arb_rtc_event("ARB_ROUTE_POLICY_APPLIED"),
    arb_rtc_event("ARB_ROUTE_CONFLICT_RECORDED"),
    arb_rtc_event("ARB_ROUTING_RECEIPT_CREATED"),
    arb_rtc_event("ARB_LOCAL_IPB_ROUTE_SELECTED"),
    arb_rtc_event("ARB_OPERATOR_POWER_OPB_ROUTE_SELECTED"),
    arb_rtc_event("ARB_INFRASTRUCTURE_EGI_ROUTE_SELECTED"),
    arb_rtc_event("ARB_SILENCE_ROUTE_SELECTED"),
    arb_rtc_event("ARB_TRUST_CALIBRATION_ROUTE_SELECTED"),
    arb_rtc_event("ARB_AUTHORITY_CHAIN_ROUTE_SELECTED"),
    arb_rtc_event("ARB_OPERATOR_REVIEW_ROUTE_SELECTED"),
    arb_rtc_event("ARB_FORBIDDEN_ROUTE_REFUSED"),
    arb_rtc_event("ARB_UNKNOWN_SIGNAL_FAILED_CLOSED"),
    arb_rtc_event("ARB_AUTHORITY_CONVERSION_CONTAINED"),
    arb_rtc_event("ARB_SIGNAL_REFUSED"),
)


def planned_arb_event_refs() -> tuple[dict[str, Any], ...]:
    return ARB_EVENT_REFS


_ROUTE_EVENT_MAP: dict[str, str] = {
    "local_ipb": "ARB_LOCAL_IPB_ROUTE_SELECTED",
    "operator_power_opb": "ARB_OPERATOR_POWER_OPB_ROUTE_SELECTED",
    "infrastructure_gap_egi": "ARB_INFRASTRUCTURE_EGI_ROUTE_SELECTED",
    "silence_sil": "ARB_SILENCE_ROUTE_SELECTED",
    "trust_calibration_trb_cal": "ARB_TRUST_CALIBRATION_ROUTE_SELECTED",
    "authority_chain_soar_hal_gpp_ueak": "ARB_AUTHORITY_CHAIN_ROUTE_SELECTED",
    "operator_review": "ARB_OPERATOR_REVIEW_ROUTE_SELECTED",
    "forbidden": "ARB_FORBIDDEN_ROUTE_REFUSED",
    "unknown_fail_closed": "ARB_UNKNOWN_SIGNAL_FAILED_CLOSED",
}


def route_selection_event(route_class: str) -> str | None:
    return _ROUTE_EVENT_MAP.get(route_class)


_L1_L9_LAYERS = frozenset(
    {
        "L1_DNI",
        "L2_RXL",
        "L3_CGL",
        "L4_RGL",
        "L5_SCL",
        "L6_IIL",
        "L7_SAB",
        "L8_IAB",
        "L9_TRL",
    }
)


def signal_recorded_event(source_layer: str) -> str:
    if source_layer in _L1_L9_LAYERS:
        return "ARB_L1_L9_SIGNAL_RECORDED"
    return "ARB_AGENT0_SIGNAL_RECORDED"


__all__ = [
    "ARB_EVENT_REFS",
    "planned_arb_event_refs",
    "route_selection_event",
    "signal_recorded_event",
]
