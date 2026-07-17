"""IMB planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.imb_cluster.rtc_design import imb_rtc_event

IMB_EVENT_REFS: tuple[dict[str, Any], ...] = (
    imb_rtc_event("IMB_INTERNAL_MODULE_CLAIM_RECORDED"),
    imb_rtc_event("IMB_INTERNAL_CONFLICT_DETECTED"),
    imb_rtc_event("IMB_MEDIATION_POLICY_APPLIED"),
    imb_rtc_event("IMB_MEDIATION_DECISION_RECORDED"),
    imb_rtc_event("IMB_MEDIATION_RECEIPT_CREATED"),
    imb_rtc_event("IMB_FAIL_CLOSED_SELECTED"),
    imb_rtc_event("IMB_OPERATOR_REVIEW_SELECTED"),
    imb_rtc_event("IMB_AUTHORITY_CHAIN_SELECTED"),
    imb_rtc_event("IMB_SILENCE_SELECTED"),
    imb_rtc_event("IMB_INTERNAL_CONSENSUS_REFUSED_AS_AUTHORITY"),
    imb_rtc_event("IMB_AUTHORITY_CONVERSION_CONTAINED"),
    imb_rtc_event("IMB_SIGNAL_REFUSED"),
)


def planned_imb_event_refs() -> tuple[dict[str, Any], ...]:
    return IMB_EVENT_REFS


_RESOLUTION_EVENT_MAP: dict[str, str] = {
    "route_to_ORI": "IMB_OPERATOR_REVIEW_SELECTED",
    "route_to_SOAR_HAL_GPP_UEAK": "IMB_AUTHORITY_CHAIN_SELECTED",
    "route_to_SIL": "IMB_SILENCE_SELECTED",
    "fail_closed": "IMB_FAIL_CLOSED_SELECTED",
    "unknown_fail_closed": "IMB_FAIL_CLOSED_SELECTED",
}


def mediation_selection_event(resolution: str) -> str | None:
    return _RESOLUTION_EVENT_MAP.get(resolution)


__all__ = [
    "IMB_EVENT_REFS",
    "mediation_selection_event",
    "planned_imb_event_refs",
]
