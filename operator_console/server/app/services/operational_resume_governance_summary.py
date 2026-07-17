from __future__ import annotations

from typing import Any

from .identity_continuity_summary import build_identity_continuity_summary
from .post_rebuild_continuity_check import load_post_rebuild_continuity_check


def build_operational_resume_governance_summary(
    *,
    root,
    binding: dict[str, Any] | None,
    task_names: list[str] | None,
    linked_tasks: list[dict[str, Any]] | None = None,
    continuity_recovery_readiness: dict[str, Any] | None,
    continuity_repair_plan: dict[str, Any] | None,
    identity_restore_validation: dict[str, Any] | None = None,
    supervised_resume_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    binding = binding if isinstance(binding, dict) else {}
    task_names = [str(item or "").strip() for item in (task_names or []) if str(item or "").strip()]
    linked_tasks = linked_tasks if isinstance(linked_tasks, list) else []
    continuity_recovery_readiness = continuity_recovery_readiness if isinstance(continuity_recovery_readiness, dict) else {}
    continuity_repair_plan = continuity_repair_plan if isinstance(continuity_repair_plan, dict) else {}
    identity_restore_validation = identity_restore_validation if isinstance(identity_restore_validation, dict) else {}
    supervised_resume_validation = supervised_resume_validation if isinstance(supervised_resume_validation, dict) else {}

    linked_by_id = {
        str(item.get("id") or "").strip(): item
        for item in linked_tasks
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }

    rebuild_checks: list[dict[str, Any]] = []
    required_actions: list[str] = []
    for check in continuity_repair_plan.get("open_checks") or []:
        if isinstance(check, str) and check not in required_actions:
            required_actions.append(check)

    blocked = list(continuity_recovery_readiness.get("blocking") or [])
    cautions = list(continuity_recovery_readiness.get("cautions") or [])

    for task_name in task_names:
        session_target = str((linked_by_id.get(task_name) or {}).get("session_target") or task_name).strip() or task_name
        identity_session_target = str(binding.get("operational_session_target") or "").strip() or session_target
        identity_continuity_summary = build_identity_continuity_summary(
            root=root,
            task_name=task_name,
            session_target=identity_session_target,
            binding=binding,
        )
        post_rebuild_continuity_check = load_post_rebuild_continuity_check(
            root=root,
            binding=binding,
            session_target=session_target,
            identity_continuity_summary=identity_continuity_summary,
            continuity_recovery_readiness=continuity_recovery_readiness,
        )
        rebuild_checks.append(
            {
                "task_name": task_name,
                "session_target": session_target,
                "status": post_rebuild_continuity_check.get("status"),
                "verification_required": bool(post_rebuild_continuity_check.get("verification_required")),
                "verified": bool(post_rebuild_continuity_check.get("verified")),
                "rebuild_recorded_at": post_rebuild_continuity_check.get("rebuild_recorded_at"),
                "verified_at": post_rebuild_continuity_check.get("verified_at"),
                "summary": post_rebuild_continuity_check.get("summary"),
            }
        )
        if post_rebuild_continuity_check.get("status") == "blocked":
            if "post_rebuild_continuity_check_blocked" not in blocked:
                blocked.append("post_rebuild_continuity_check_blocked")
        elif post_rebuild_continuity_check.get("status") == "pending":
            if "post_rebuild_continuity_check_pending" not in cautions:
                cautions.append("post_rebuild_continuity_check_pending")
            action = f"verify_post_rebuild_continuity:{task_name}"
            if action not in required_actions:
                required_actions.append(action)

    if bool(identity_restore_validation.get("required")):
        restore_status = str(identity_restore_validation.get("status") or "").strip().lower()
        if restore_status == "blocked":
            if "identity_restore_validation_blocked" not in blocked:
                blocked.append("identity_restore_validation_blocked")
        elif restore_status != "validated":
            if "identity_restore_validation_pending" not in cautions:
                cautions.append("identity_restore_validation_pending")
            if "verify_identity_restore" not in required_actions:
                required_actions.append("verify_identity_restore")
    if bool(supervised_resume_validation.get("required")) and not bool(supervised_resume_validation.get("validated")):
        if "supervised_resume_validation_pending" not in cautions:
            cautions.append("supervised_resume_validation_pending")
        if "run_supervised_resume_validation" not in required_actions:
            required_actions.append("run_supervised_resume_validation")

    if blocked:
        status = "blocked"
    elif cautions:
        status = "caution"
    else:
        status = "ready"

    verified_count = sum(1 for item in rebuild_checks if item.get("verified"))
    pending_count = sum(1 for item in rebuild_checks if item.get("status") == "pending")
    blocked_count = sum(1 for item in rebuild_checks if item.get("status") == "blocked")
    verification_required_count = sum(1 for item in rebuild_checks if item.get("verification_required"))

    if status == "ready":
        summary = "operational_resume_ready"
    elif blocked:
        summary = blocked[0]
    elif cautions:
        summary = cautions[0]
    else:
        summary = "operational_resume_unknown"

    return {
        "status": status,
        "resume_ready": status == "ready",
        "blocking": blocked,
        "cautions": cautions,
        "required_actions": required_actions,
        "task_count": len(task_names),
        "verification_required_count": verification_required_count,
        "verified_count": verified_count,
        "pending_count": pending_count,
        "blocked_count": blocked_count,
        "task_checks": rebuild_checks,
        "identity_restore_validation": identity_restore_validation,
        "supervised_resume_validation": supervised_resume_validation,
        "summary": summary,
    }
