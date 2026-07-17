from __future__ import annotations

from typing import Any


def build_continuity_recovery_readiness(
    *,
    identity_continuity_summary: dict[str, Any] | None,
    continuity_incident_summary: dict[str, Any] | None,
    continuity_recovery_ack: dict[str, Any] | None = None,
    continuity_repair_observation: dict[str, Any] | None = None,
    identity_resume_observation: dict[str, Any] | None = None,
    post_rebuild_continuity_check: dict[str, Any] | None = None,
    identity_restore_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identity_continuity_summary = identity_continuity_summary if isinstance(identity_continuity_summary, dict) else {}
    continuity_incident_summary = continuity_incident_summary if isinstance(continuity_incident_summary, dict) else {}
    continuity_recovery_ack = continuity_recovery_ack if isinstance(continuity_recovery_ack, dict) else {}
    continuity_repair_observation = continuity_repair_observation if isinstance(continuity_repair_observation, dict) else {}
    identity_resume_observation = identity_resume_observation if isinstance(identity_resume_observation, dict) else {}
    post_rebuild_continuity_check = post_rebuild_continuity_check if isinstance(post_rebuild_continuity_check, dict) else {}
    identity_restore_validation = identity_restore_validation if isinstance(identity_restore_validation, dict) else {}

    blocking: list[str] = []
    cautions: list[str] = []

    identity_status = str(identity_continuity_summary.get("status") or "").strip().lower()
    incident_status = str(continuity_incident_summary.get("status") or "").strip().lower()
    acknowledged = bool(continuity_recovery_ack.get("acknowledged"))
    observation_complete = bool(continuity_repair_observation.get("observation_complete"))
    recovered_and_closed = incident_status == "recovered" and acknowledged and observation_complete

    if identity_status == "missing":
        blocking.append("identity_continuity_missing")
    elif identity_status == "partial" and not recovered_and_closed:
        cautions.append("identity_continuity_partial")
    if identity_resume_observation.get("observation_required") and not identity_resume_observation.get("observation_complete"):
        cautions.append("identity_resume_observation_pending")

    if incident_status == "active":
        blocking.append("active_continuity_incident")
    elif incident_status == "recovered":
        if continuity_repair_observation.get("observation_required") and not observation_complete:
            cautions.append("post_repair_observation_pending")
        if not recovered_and_closed:
            cautions.append("recent_continuity_recovery")
    post_rebuild_status = str(post_rebuild_continuity_check.get("status") or "").strip().lower()
    if bool(post_rebuild_continuity_check.get("verification_required")):
        if post_rebuild_status == "blocked":
            blocking.append("post_rebuild_continuity_check_blocked")
        elif post_rebuild_status != "verified":
            cautions.append("post_rebuild_continuity_check_pending")
    if bool(identity_restore_validation.get("required")):
        restore_status = str(identity_restore_validation.get("status") or "").strip().lower()
        if restore_status == "blocked":
            blocking.append("identity_restore_validation_blocked")
        elif restore_status != "validated":
            cautions.append("identity_restore_validation_pending")

    status = "ready"
    if blocking:
        status = "blocked"
    elif cautions:
        status = "caution"

    resume_permitted = status == "ready" or (status == "caution" and acknowledged)
    repair_required = status in {"blocked", "caution"}

    latest_event_detail = str(continuity_incident_summary.get("latest_event_detail") or "").strip() or None
    continuity_anchor = str(identity_continuity_summary.get("continuity_anchor") or "").strip() or None
    summary = continuity_anchor or latest_event_detail
    recovery_closeout_complete = incident_status != "recovered" or (acknowledged and observation_complete and not cautions and not blocking)

    return {
        "status": status,
        "safe_to_resume": status == "ready",
        "resume_permitted": resume_permitted,
        "repair_required": repair_required,
        "acknowledged": acknowledged,
        "acknowledged_at": continuity_recovery_ack.get("acknowledged_at"),
        "acknowledged_by": continuity_recovery_ack.get("acknowledged_by"),
        "ack_note": continuity_recovery_ack.get("note"),
        "can_acknowledge": status == "caution",
        "blocking": blocking,
        "cautions": cautions,
        "identity_status": identity_status or None,
        "incident_status": incident_status or None,
        "continuity_anchor": continuity_anchor,
        "latest_event_at": continuity_incident_summary.get("latest_event_at"),
        "latest_event_kind": continuity_incident_summary.get("latest_event_kind"),
        "latest_event_detail": latest_event_detail,
        "summary": summary,
        "post_repair_observation": continuity_repair_observation,
        "identity_resume_observation": identity_resume_observation,
        "post_rebuild_continuity_check": post_rebuild_continuity_check,
        "identity_restore_validation": identity_restore_validation,
        "recovery_closeout_complete": recovery_closeout_complete,
    }
