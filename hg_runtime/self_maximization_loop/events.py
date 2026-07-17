"""SML planned RTC event design — first safe slice, no live emission."""

from __future__ import annotations

from typing import Any

from hg_core.signaling.rtc_design import signaling_rtc_event

SML_EVENT_REFS: tuple[dict[str, Any], ...] = (
    signaling_rtc_event("SML_CYCLE_STARTED"),
    signaling_rtc_event("SML_DESIRE_PATTERN_RECORDED"),
    signaling_rtc_event("SML_ENVIRONMENT_SUMMARY_RECORDED"),
    signaling_rtc_event("SML_MENTALITY_ADJUSTMENT_RECOMMENDED"),
    signaling_rtc_event("SML_APPEARANCE_ADAPTATION_RECOMMENDED"),
    signaling_rtc_event("SML_BEHAVIOR_OPTION_RECOMMENDED"),
    signaling_rtc_event("SML_SITUATION_ASSESSED"),
    signaling_rtc_event("SML_FEEDBACK_RECORDED"),
    signaling_rtc_event("SML_IMPROVEMENT_HYPOTHESIS_RECORDED"),
    signaling_rtc_event("SML_NEGATIVE_FEEDBACK_PRESERVED"),
    signaling_rtc_event("SML_SELF_OPTIMIZATION_BYPASS_CONTAINED"),
    signaling_rtc_event("SML_CYCLE_COMPLETED"),
    signaling_rtc_event("SML_CYCLE_REFUSED"),
    signaling_rtc_event("SML_SIGNAL_REFUSED"),
    signaling_rtc_event("SML_CONTAINMENT_WAIVED_RECORDED"),
)


def planned_sml_event_refs() -> tuple[dict[str, Any], ...]:
    return SML_EVENT_REFS


__all__ = ["SML_EVENT_REFS", "planned_sml_event_refs"]
