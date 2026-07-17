"""EOG cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.embodiment_oea_cluster.rtc_design import eog_rtc_event

EOG_EVENT_REFS: tuple[dict[str, Any], ...] = (
    eog_rtc_event("EOG_BODY_INTEGRATION_RECORDED"),
    eog_rtc_event("EOG_GROWTH_REQUEST_RECORDED"),
    eog_rtc_event("EOG_GROWTH_ASSESSMENT_CREATED"),
    eog_rtc_event("EOG_GROWTH_DECISION_RECORDED"),
    eog_rtc_event("EOG_EMBODIMENT_IMPLIES_CONSENT_REFUSED"),
    eog_rtc_event("EOG_HARDWARE_REACH_REFUSED"),
    eog_rtc_event("EOG_OEA_CATALOG_BYPASS_REFUSED"),
    eog_rtc_event("EOG_HARDWARE_OFF_BACKBURNER_REFUSED"),
    eog_rtc_event("EOG_STALE_APPROVAL_REFUSED"),
    eog_rtc_event("EOG_SECRET_LEAKAGE_REFUSED"),
    eog_rtc_event("EOG_AUTHORITY_CONVERSION_CONTAINED"),
    eog_rtc_event("EOG_FAKE_QUEUE_ENQUEUED"),
    eog_rtc_event("EOG_AUTHORITY_CHAIN_PROPOSAL_DISPATCHED"),
    eog_rtc_event("EOG_OEA_CATALOG_RECORDED"),
    eog_rtc_event("EOG_PRO_BODY_STATE_LINKED"),
    eog_rtc_event("EOG_BACKBURNER_GUARD_ACTIVE"),
)


def planned_eog_event_refs() -> tuple[dict[str, Any], ...]:
    return EOG_EVENT_REFS


__all__ = ["EOG_EVENT_REFS", "planned_eog_event_refs"]
