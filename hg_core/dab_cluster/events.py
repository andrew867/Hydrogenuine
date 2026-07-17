"""DAB cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.dab_cluster.rtc_design import dab_rtc_event

DAB_EVENT_REFS: tuple[dict[str, Any], ...] = (
        dab_rtc_event("DAB_DIGESTION_REQUEST_RECORDED"),
dab_rtc_event("DAB_DIGEST_PACKET_CREATED"),
dab_rtc_event("DAB_ASSIMILATION_CANDIDATE_CREATED"),
dab_rtc_event("DAB_MEMORY_PROPOSAL_CREATED"),
dab_rtc_event("DAB_TOOL_PROPOSAL_CREATED"),
dab_rtc_event("DAB_EVIDENCE_PROPOSAL_CREATED"),
dab_rtc_event("DAB_WASTE_CANDIDATE_CREATED"),
dab_rtc_event("DAB_POISON_REFUSED"),
dab_rtc_event("DAB_AUTHORITY_CONVERSION_REFUSED"),
dab_rtc_event("DAB_FAILED_CLOSED"),
)


def planned_dab_event_refs() -> tuple[dict[str, Any], ...]:
    return DAB_EVENT_REFS


__all__ = ["DAB_EVENT_REFS", "planned_dab_event_refs"]

