from __future__ import annotations

from typing import Any


def build_continuity_repair_plan(
    *,
    identity_continuity_summary: dict[str, Any] | None,
    identity_resume_procedure: dict[str, Any] | None = None,
    identity_resume_observation: dict[str, Any] | None = None,
    continuity_incident_summary: dict[str, Any] | None,
    continuity_recovery_readiness: dict[str, Any] | None,
    continuity_repair_observation: dict[str, Any] | None = None,
    post_rebuild_continuity_check: dict[str, Any] | None = None,
    identity_restore_validation: dict[str, Any] | None = None,
    supervised_resume_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identity_continuity_summary = identity_continuity_summary if isinstance(identity_continuity_summary, dict) else {}
    identity_resume_procedure = identity_resume_procedure if isinstance(identity_resume_procedure, dict) else {}
    identity_resume_observation = identity_resume_observation if isinstance(identity_resume_observation, dict) else {}
    continuity_incident_summary = continuity_incident_summary if isinstance(continuity_incident_summary, dict) else {}
    continuity_recovery_readiness = continuity_recovery_readiness if isinstance(continuity_recovery_readiness, dict) else {}
    continuity_repair_observation = continuity_repair_observation if isinstance(continuity_repair_observation, dict) else {}
    post_rebuild_continuity_check = post_rebuild_continuity_check if isinstance(post_rebuild_continuity_check, dict) else {}
    identity_restore_validation = identity_restore_validation if isinstance(identity_restore_validation, dict) else {}
    supervised_resume_validation = supervised_resume_validation if isinstance(supervised_resume_validation, dict) else {}

    identity_status = str(identity_continuity_summary.get("status") or "").strip().lower()
    incident_status = str(continuity_incident_summary.get("status") or "").strip().lower()
    readiness_status = str(continuity_recovery_readiness.get("status") or "").strip().lower()
    acknowledged = bool(continuity_recovery_readiness.get("acknowledged"))

    open_checks: list[str] = []
    completed_checks: list[str] = []

    if identity_status == "missing":
        open_checks.append("restore_identity_continuity")
    elif identity_status in {"partial", "healthy"}:
        completed_checks.append("identity_continuity_present")
    for step in identity_resume_procedure.get("open_steps") or []:
        if step not in open_checks:
            open_checks.append(step)
    for step in identity_resume_procedure.get("completed_steps") or []:
        if step not in completed_checks:
            completed_checks.append(step)
    if identity_resume_observation.get("observation_required"):
        if identity_resume_observation.get("observation_complete"):
            completed_checks.append("observe_first_identity_resume_cycle")
        else:
            open_checks.append("observe_first_identity_resume_cycle")

    if incident_status == "active":
        open_checks.append("replace_or_rebind_damaged_session")
        open_checks.append("verify_continuity_artifacts")
    elif incident_status == "recovered":
        completed_checks.append("continuity_repair_detected")
        if not acknowledged:
            open_checks.append("acknowledge_bounded_resume")
        if continuity_repair_observation.get("observation_required"):
            if continuity_repair_observation.get("observation_complete"):
                completed_checks.append("observe_first_post_repair_cycle")
            else:
                open_checks.append("observe_first_post_repair_cycle")
    else:
        completed_checks.append("no_active_continuity_incident")

    if readiness_status == "ready":
        completed_checks.append("resume_ready")
        if incident_status == "recovered":
            completed_checks.append("post_repair_resume_ready")
    elif readiness_status == "caution" and acknowledged:
        completed_checks.append("bounded_resume_acknowledged")

    if post_rebuild_continuity_check.get("verification_required"):
        if post_rebuild_continuity_check.get("verified"):
            completed_checks.append("verify_post_rebuild_continuity")
        else:
            open_checks.append("verify_post_rebuild_continuity")
    if identity_restore_validation.get("required"):
        if identity_restore_validation.get("verified"):
            completed_checks.append("verify_identity_restore")
        else:
            open_checks.append("verify_identity_restore")
    if supervised_resume_validation.get("required"):
        if supervised_resume_validation.get("validated"):
            completed_checks.append("run_supervised_resume_validation")
        else:
            open_checks.append("run_supervised_resume_validation")

    if readiness_status == "blocked":
        status = "repair_required"
    elif readiness_status == "caution":
        status = "observe_before_resume"
    else:
        status = "clean"

    return {
        "status": status,
        "repair_required": status != "clean",
        "open_check_count": len(open_checks),
        "completed_check_count": len(completed_checks),
        "open_checks": open_checks,
        "completed_checks": completed_checks,
        "latest_event_detail": continuity_recovery_readiness.get("latest_event_detail"),
        "identity_resume_observation": identity_resume_observation,
        "post_repair_observation": continuity_repair_observation,
        "post_rebuild_continuity_check": post_rebuild_continuity_check,
        "identity_restore_validation": identity_restore_validation,
        "supervised_resume_validation": supervised_resume_validation,
        "summary": open_checks[0] if open_checks else "continuity_clear",
    }
