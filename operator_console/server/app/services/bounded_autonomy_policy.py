from __future__ import annotations

from typing import Any


def build_bounded_autonomy_policy_summary(
    *,
    agency_control_summary: dict[str, Any] | None,
    continuity_recovery_readiness: dict[str, Any] | None,
    operational_resume_governance_summary: dict[str, Any] | None,
    operational_resume_checkpoint: dict[str, Any] | None,
    identity_restore_validation: dict[str, Any] | None = None,
    supervised_resume_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    agency_control_summary = agency_control_summary if isinstance(agency_control_summary, dict) else {}
    continuity_recovery_readiness = continuity_recovery_readiness if isinstance(continuity_recovery_readiness, dict) else {}
    operational_resume_governance_summary = operational_resume_governance_summary if isinstance(operational_resume_governance_summary, dict) else {}
    operational_resume_checkpoint = operational_resume_checkpoint if isinstance(operational_resume_checkpoint, dict) else {}
    identity_restore_validation = identity_restore_validation if isinstance(identity_restore_validation, dict) else {}
    supervised_resume_validation = supervised_resume_validation if isinstance(supervised_resume_validation, dict) else {}

    blockers: list[str] = []
    required_actions: list[str] = []
    action_hint = None
    next_eligible_at = None

    mode = str(agency_control_summary.get("effective_mode") or agency_control_summary.get("mode") or "normal").strip().lower()
    lane_policy = str(agency_control_summary.get("outbound_lane_policy") or "unrestricted").strip().lower()
    if mode == "held":
        blockers.append("agency_hold")
    elif mode == "review_only":
        blockers.append("review_gate")
    if bool(agency_control_summary.get("outbound_budget_exhausted")):
        blockers.append("outbound_budget")
        next_eligible_at = agency_control_summary.get("outbound_budget_next_reset_at")
    if lane_policy in {"drafts_only", "blocked"}:
        blockers.append(f"lane_policy:{lane_policy}")

    continuity_status = str(continuity_recovery_readiness.get("status") or "").strip().lower()
    if continuity_status == "blocked":
        blockers.append("continuity_recovery")
    elif continuity_status == "caution" and not bool(continuity_recovery_readiness.get("acknowledged")):
        blockers.append("continuity_recovery_ack_required")
        required_actions.append("acknowledge_recovery")
        action_hint = action_hint or "Acknowledge bounded continuity recovery before release."

    if bool(identity_restore_validation.get("required")) and not bool(identity_restore_validation.get("verified")):
        blockers.append("identity_restore_validation_required")
        required_actions.append("verify_identity_restore")
        action_hint = action_hint or "Verify identity wake/sleep continuity after restore before release."

    if str(operational_resume_governance_summary.get("status") or "").strip().lower() == "ready" and not bool(operational_resume_checkpoint.get("approved")):
        blockers.append("operational_resume_checkpoint_required")
        required_actions.append("approve_resume")
        action_hint = action_hint or "Approve a fresh operational resume checkpoint before release."

    if bool(supervised_resume_validation.get("required")) and not bool(supervised_resume_validation.get("validated")):
        blockers.append("supervised_resume_validation_required")
        required_actions.append("run_supervised_resume_validation")
        action_hint = action_hint or "Run the supervised resume validation checklist before release."

    if blockers:
        status = "blocked"
    elif str(operational_resume_governance_summary.get("status") or "").strip().lower() == "caution":
        status = "caution"
    else:
        status = "ready"

    return {
        "status": status,
        "blockers": blockers,
        "required_actions": required_actions,
        "next_eligible_at": next_eligible_at,
        "action_hint": action_hint,
        "summary": blockers[0] if blockers else "bounded_autonomy_ready",
    }
