"""P69 field trial readiness boundary domain logic."""

from __future__ import annotations

from hg_runtime.field_trial_readiness_boundary.schemas import (
    reject_readiness_overreach,
)


def validate_readiness_checklist(checklist: dict) -> list[str]:
    issues = []
    if not checklist.get("checklist_id"):
        issues.append("missing_checklist_id")
    if not checklist.get("operator_approval_required"):
        issues.append("operator_approval_must_be_required")
    if checklist.get("is_live_trial"):
        issues.append("readiness_must_not_be_live_trial")
    if checklist.get("is_deployment_permission"):
        issues.append("readiness_must_not_be_deployment_permission")
    reject_readiness_overreach(checklist)
    return issues


def validate_field_scenario(scenario: dict) -> list[str]:
    issues = []
    if not scenario.get("scenario_id"):
        issues.append("missing_scenario_id")
    if scenario.get("live_effects_required"):
        issues.append("live_effects_not_allowed")
    if not scenario.get("operator_approval_required"):
        issues.append("operator_approval_must_be_required")
    return issues


def validate_rehearsal(rehearsal: dict) -> list[str]:
    issues = []
    if not rehearsal.get("rehearsal_id"):
        issues.append("missing_rehearsal_id")
    if rehearsal.get("is_live_trial"):
        issues.append("rehearsal_must_not_be_live_trial")
    if rehearsal.get("live_effects_detected"):
        issues.append("no_live_effects_in_rehearsal")
    return issues


def validate_readiness_gap(gap: dict) -> list[str]:
    issues = []
    if not gap.get("gap_id"):
        issues.append("missing_gap_id")
    if gap.get("is_failure_laundering"):
        issues.append("gap_must_not_launder_failure")
    return issues
