"""REB static long-gap and adversarial policies."""

from __future__ import annotations

from typing import Any

from hg_runtime.reentry_boundary.types import GapBand, ReEntryDecisionClass, ReEntryMode

_GAP_POLICIES: dict[GapBand, dict[str, Any]] = {
    "under_1_hour": {
        "policy_id": "reb-gap-under-1-hour",
        "minimum_reentry_mode": "observe_only",
        "required_refreshes": ("tim:freshness",),
        "required_reviews": (),
        "forbidden_assumptions": ("expired_approval_current",),
        "allowed_continuity_claim": "weak_contextual",
        "default_decision": "allow_observe_only",
    },
    "1_to_24_hours": {
        "policy_id": "reb-gap-1-to-24-hours",
        "minimum_reentry_mode": "observe_only",
        "required_refreshes": ("tim:freshness", "task:refresh"),
        "required_reviews": (),
        "forbidden_assumptions": ("stale_context_hidden",),
        "allowed_continuity_claim": "weak_contextual",
        "default_decision": "require_TIM_refresh",
    },
    "1_to_7_days": {
        "policy_id": "reb-gap-1-to-7-days",
        "minimum_reentry_mode": "summarize",
        "required_refreshes": ("tim:freshness", "task:refresh", "state:refresh"),
        "required_reviews": ("ori:operator-visible-summary",),
        "forbidden_assumptions": ("mission_current",),
        "allowed_continuity_claim": "memory_linked",
        "default_decision": "require_operator_review",
    },
    "1_to_30_days": {
        "policy_id": "reb-gap-1-to-30-days",
        "minimum_reentry_mode": "summarize",
        "required_refreshes": ("tim:freshness", "ret:review", "obligation:review", "risk:review"),
        "required_reviews": ("tim:refresh", "ret:review"),
        "forbidden_assumptions": ("execution_continuation_without_chain",),
        "allowed_continuity_claim": "memory_linked",
        "default_decision": "require_RET_review",
    },
    "1_to_12_months": {
        "policy_id": "reb-gap-1-to-12-months",
        "minimum_reentry_mode": "summarize",
        "required_refreshes": ("tim:freshness", "policy:refresh", "world_state:refresh"),
        "required_reviews": ("operator:review", "trb_cal:review"),
        "forbidden_assumptions": ("strong_continuity_claim",),
        "allowed_continuity_claim": "memory_linked",
        "default_decision": "require_TRB_CAL_review",
    },
    "1_to_10_years": {
        "policy_id": "reb-gap-1-to-10-years",
        "minimum_reentry_mode": "observe_only",
        "required_refreshes": ("bootstrap:reentry", "policy:refresh", "world_state:refresh", "dependency:refresh"),
        "required_reviews": ("operator:review",),
        "forbidden_assumptions": ("mission_current", "authority_inherited"),
        "allowed_continuity_claim": "weak_contextual",
        "default_decision": "require_operator_review",
    },
    "over_10_years": {
        "policy_id": "reb-gap-over-10-years",
        "minimum_reentry_mode": "observe_only",
        "required_refreshes": ("archival:reentry",),
        "required_reviews": ("operator:review", "cnt:review"),
        "forbidden_assumptions": ("current_world_assumptions", "strong_continuity_claim"),
        "allowed_continuity_claim": "none",
        "default_decision": "allow_summary_only",
    },
    "over_50_years": {
        "policy_id": "reb-gap-over-50-years",
        "minimum_reentry_mode": "observe_only",
        "required_refreshes": ("bootstrap:reentry", "archival:reentry"),
        "required_reviews": ("operator:review", "mor:review", "cnt:review"),
        "forbidden_assumptions": (
            "current_world_assumptions",
            "authority_inheritance",
            "mission_continuity",
        ),
        "allowed_continuity_claim": "invalid",
        "default_decision": "deny_reentry",
    },
    "unknown": {
        "policy_id": "reb-gap-unknown",
        "minimum_reentry_mode": "unknown",
        "required_refreshes": ("tim:freshness",),
        "required_reviews": ("operator:review",),
        "forbidden_assumptions": ("assume_continuity",),
        "allowed_continuity_claim": "unknown",
        "default_decision": "unknown_fail_closed",
    },
}

_ADVERSARIAL_POLICIES: dict[str, dict[str, Any]] = {
    "stale_approval": {
        "decision": "fail_closed",
        "reason_code": "reb.refused.stale_approval",
        "forbidden_effects": ("restore_expired_approval",),
    },
    "revoked_permit": {
        "decision": "fail_closed",
        "reason_code": "reb.refused.revoked_permit",
        "forbidden_effects": ("restore_revoked_permit",),
    },
    "checkpoint_authority": {
        "decision": "deny_reentry",
        "reason_code": "reb.refused.checkpoint_authority",
        "forbidden_effects": ("treat_checkpoint_as_authority",),
    },
    "stale_memory_as_current": {
        "decision": "fail_closed",
        "reason_code": "reb.refused.stale_memory_as_current",
        "forbidden_effects": ("treat_stale_memory_as_current",),
    },
    "continuity_claim": {
        "decision": "deny_reentry",
        "reason_code": "reb.refused.continuity_claim",
        "forbidden_effects": ("continuity_as_identity",),
    },
    "operator_absence_as_approval": {
        "decision": "fail_closed",
        "reason_code": "reb.refused.operator_absence_as_approval",
        "forbidden_effects": ("operator_absence_as_approval",),
    },
    "old_mission_as_current": {
        "decision": "require_operator_review",
        "reason_code": "reb.refused.old_mission_as_current",
        "forbidden_effects": ("resume_old_mission_without_review",),
    },
    "reentry_packet_as_permission": {
        "decision": "fail_closed",
        "reason_code": "reb.refused.reentry_packet_as_permission",
        "forbidden_effects": ("packet_as_permission",),
    },
    "execution_resume": {
        "decision": "require_authority_chain",
        "reason_code": "reb.refused.execution_resume",
        "forbidden_effects": ("resume_external_action", "oea_ter_call"),
    },
}


def policy_for_gap_band(gap_band: GapBand) -> dict[str, Any]:
    return dict(_GAP_POLICIES.get(gap_band, _GAP_POLICIES["unknown"]))


def policy_for_adversarial(signal: str) -> dict[str, Any] | None:
    return _ADVERSARIAL_POLICIES.get(signal)


def decision_for_mode_and_gap(
    requested_mode: ReEntryMode,
    gap_band: GapBand,
    *,
    tim_fresh: bool,
) -> ReEntryDecisionClass:
    if requested_mode == "resume_execution_candidate":
        return "require_authority_chain"
    if requested_mode == "restore_checkpoint":
        return "deny_reentry"
    gap_policy = policy_for_gap_band(gap_band)
    default = gap_policy["default_decision"]
    if gap_band == "under_1_hour" and tim_fresh and requested_mode in {"observe_only", "speak"}:
        if requested_mode == "speak":
            return "allow_speak_with_disclosure"
        return "allow_observe_only"
    if gap_band == "over_50_years":
        return "deny_reentry"
    return default  # type: ignore[return-value]


__all__ = [
    "decision_for_mode_and_gap",
    "policy_for_adversarial",
    "policy_for_gap_band",
]
