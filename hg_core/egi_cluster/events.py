"""EGI cluster planned RTC event refs."""

from __future__ import annotations

from typing import Any

from hg_core.egi_cluster.rtc_design import egi_rtc_event

EGI_EVENT_REFS: tuple[dict[str, Any], ...] = (
    egi_rtc_event("EGI_BEHAVIOR_OBSERVED"),
    egi_rtc_event("EGI_REPEATED_PATTERN_DETECTED"),
    egi_rtc_event("EGI_CAPABILITY_GAP_RECORDED"),
    egi_rtc_event("EGI_INFRASTRUCTURE_PROPOSAL_CREATED"),
    egi_rtc_event("EGI_BUILD_REQUEST_DRAFTED"),
    egi_rtc_event("EGI_OPERATOR_APPROVAL_PACKET_CREATED"),
    egi_rtc_event("EGI_OPERATOR_APPROVED"),
    egi_rtc_event("EGI_OPERATOR_REJECTED"),
    egi_rtc_event("EGI_REQUEST_EXPIRED"),
    egi_rtc_event("EGI_BUILD_REQUEST_ROUTED_TO_CODE_SIDE"),
    egi_rtc_event("EGI_IMPLEMENTATION_AUDIT_REQUIRED"),
    egi_rtc_event("EGI_AUTHORITY_CONVERSION_CONTAINED"),
    egi_rtc_event("EGI_SELF_MODIFICATION_REFUSED"),
    egi_rtc_event("EGI_TOOL_PERMISSION_REFUSED"),
    egi_rtc_event("EGI_SIGNAL_REFUSED"),
)


def planned_egi_event_refs() -> tuple[dict[str, Any], ...]:
    return EGI_EVENT_REFS


__all__ = ["EGI_EVENT_REFS", "planned_egi_event_refs"]
