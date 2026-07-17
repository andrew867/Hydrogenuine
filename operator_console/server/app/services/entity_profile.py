from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _as_epoch(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return float("-inf")
    try:
        return float(text)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return float("-inf")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _dedupe_nonempty(values: list[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        out.append(text)
    return out


def _candidate_tokens(entity: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for key in (
        "id",
        "task_name",
        "source_task_name",
        "job_id",
        "session_target",
        "operational_session_target",
        "operational_agent_id",
        "fingerprint_id",
        "platform",
    ):
        token = _text(entity.get(key))
        if token:
            tokens.add(token.lower())
    for task in entity.get("tasks") or []:
        token = _text(task)
        if token:
            tokens.add(token.lower())
    for linked in entity.get("linked_tasks") or []:
        if not isinstance(linked, dict):
            continue
        for key in ("id", "session_target", "workflow_id", "task_name"):
            token = _text(linked.get(key))
            if token:
                tokens.add(token.lower())
    review = entity.get("review_handoff_summary") if isinstance(entity.get("review_handoff_summary"), dict) else {}
    latest = review.get("latest") if isinstance(review.get("latest"), dict) else {}
    for key in ("approval_id", "approval_href", "task_name", "refreshed_from_approval_id"):
        token = _text(latest.get(key))
        if token:
            tokens.add(token.lower())
    return tokens


def _run_matches(entity_tokens: set[str], row: dict[str, Any]) -> bool:
    row_tokens = [
        _text(row.get("run_id")),
        _text(row.get("workflow_id")),
        _text(row.get("graph_id")),
        _text(row.get("correlation_id")),
        _text(row.get("run_dir")),
    ]
    for candidate in row_tokens:
        if not candidate:
            continue
        lowered = candidate.lower()
        if lowered in entity_tokens:
            return True
        if lowered in (row.get("run_dir") or "").lower():
            return True
    return False


def _summarize_run(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": row.get("run_id"),
        "workflow_id": row.get("workflow_id") or row.get("graph_id"),
        "status": row.get("status"),
        "started_at": row.get("started_at"),
        "ended_at": row.get("ended_at"),
        "failure_class": row.get("failure_class"),
        "budget_used": row.get("budget_used") if isinstance(row.get("budget_used"), dict) else {},
        "run_dir": row.get("run_dir"),
        "summary_path": row.get("summary_path"),
        "correlation_id": row.get("correlation_id"),
    }


def _summary_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _build_continuity_view(
    entity: dict[str, Any],
    *,
    continuity_packet: dict[str, Any],
    latest_runs: list[dict[str, Any]],
    review_handoff_summary: dict[str, Any] | None = None,
    commitment_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entity_id = _text(entity.get("id"))
    task_name = _text(entity.get("task_name"))
    operational_agent_id = _text(entity.get("operational_agent_id"))
    last_wake_at = _summary_text((continuity_packet.get("identity_continuity_summary") or {}).get("last_wake_at"))
    continuity_recovery_readiness = continuity_packet.get("continuity_recovery_readiness") if isinstance(continuity_packet.get("continuity_recovery_readiness"), dict) else {}
    continuity_repair_plan = continuity_packet.get("continuity_repair_plan") if isinstance(continuity_packet.get("continuity_repair_plan"), dict) else {}
    continuity_incident_summary = continuity_packet.get("continuity_incident_summary") if isinstance(continuity_packet.get("continuity_incident_summary"), dict) else {}
    identity_resume_procedure = continuity_packet.get("identity_resume_procedure") if isinstance(continuity_packet.get("identity_resume_procedure"), dict) else {}
    operational_resume_governance_summary = continuity_packet.get("operational_resume_governance_summary") if isinstance(continuity_packet.get("operational_resume_governance_summary"), dict) else {}
    operational_resume_checkpoint = continuity_packet.get("operational_resume_checkpoint") if isinstance(continuity_packet.get("operational_resume_checkpoint"), dict) else {}
    identity_resume_observation = continuity_packet.get("identity_resume_observation") if isinstance(continuity_packet.get("identity_resume_observation"), dict) else {}
    continuity_repair_observation = continuity_packet.get("continuity_repair_observation") if isinstance(continuity_packet.get("continuity_repair_observation"), dict) else {}
    post_rebuild_continuity_check = continuity_packet.get("post_rebuild_continuity_check") if isinstance(continuity_packet.get("post_rebuild_continuity_check"), dict) else {}
    identity_restore_validation = continuity_packet.get("identity_restore_validation") if isinstance(continuity_packet.get("identity_restore_validation"), dict) else {}
    supervised_resume_validation = continuity_packet.get("supervised_resume_validation") if isinstance(continuity_packet.get("supervised_resume_validation"), dict) else {}
    continuity_quality_summary = continuity_packet.get("continuity_quality_summary") if isinstance(continuity_packet.get("continuity_quality_summary"), dict) else {}
    review_handoff_summary = review_handoff_summary if isinstance(review_handoff_summary, dict) else {}
    commitment_summary = commitment_summary if isinstance(commitment_summary, dict) else {}

    activity: dict[str, Any] = {}
    try:
        from .activity_service import get_recent_activity

        activity = get_recent_activity(
            limit_runs=max(3, len(latest_runs) or 3),
            limit_decisions=10,
            entity_id=entity_id,
            workflow_id=task_name,
            projection_view="compact",
        )
    except Exception:
        activity = {}
    activity_projection = activity.get("activity_projection") if isinstance(activity.get("activity_projection"), dict) else {}
    since_last_wake = activity_projection.get("since_last_wake") if isinstance(activity_projection.get("since_last_wake"), dict) else {}
    recent_timeline = since_last_wake.get("timeline") if isinstance(since_last_wake.get("timeline"), list) else []

    steering_profile: dict[str, Any] = {}
    steering_agent_id = operational_agent_id or entity_id or task_name
    if steering_agent_id:
        try:
            from .steering_service import get_steering_profile

            steering = get_steering_profile(steering_agent_id)
            if isinstance(steering, dict):
                steering_profile = steering
        except Exception:
            steering_profile = {}
    steering_updated_at = _summary_text(steering_profile.get("updated_at"))
    steering_version = steering_profile.get("version")
    steering_changed_since_last_wake = bool(
        steering_updated_at and last_wake_at and _as_epoch(steering_updated_at) > _as_epoch(last_wake_at)
    )

    conflicts = _dedupe_nonempty(
        [
            *(continuity_recovery_readiness.get("blocking") or []),
            *(continuity_recovery_readiness.get("cautions") or []),
            *(identity_resume_procedure.get("open_steps") or []),
            *(continuity_repair_plan.get("open_checks") or []),
            *(operational_resume_governance_summary.get("required_actions") or []),
            continuity_incident_summary.get("latest_event_detail"),
            operational_resume_checkpoint.get("invalidated_reason"),
            post_rebuild_continuity_check.get("status") if post_rebuild_continuity_check.get("status") == "blocked" else None,
            identity_restore_validation.get("status") if identity_restore_validation.get("status") == "blocked" else None,
            supervised_resume_validation.get("status") if supervised_resume_validation.get("status") == "blocked" else None,
            identity_resume_observation.get("status") if identity_resume_observation.get("observation_required") and not identity_resume_observation.get("observation_complete") else None,
            continuity_repair_observation.get("status") if continuity_repair_observation.get("observation_required") and not continuity_repair_observation.get("observation_complete") else None,
            continuity_quality_summary.get("status") if continuity_quality_summary.get("status") in {"watch", "blocked"} else None,
        ]
    )

    scheduled_work = _dedupe_nonempty(
        [
            *(identity_resume_procedure.get("open_steps") or []),
            *(continuity_repair_plan.get("open_checks") or []),
            *(continuity_recovery_readiness.get("cautions") or []),
            *(operational_resume_governance_summary.get("required_actions") or []),
            "verify_post_rebuild_continuity" if bool(post_rebuild_continuity_check.get("verification_required")) and not bool(post_rebuild_continuity_check.get("verified")) else None,
            "verify_identity_restore" if bool(identity_restore_validation.get("required")) and not bool(identity_restore_validation.get("verified")) else None,
            "run_supervised_resume_validation" if bool(supervised_resume_validation.get("required")) and not bool(supervised_resume_validation.get("validated")) else None,
            "record_wake_receipt" if not bool((continuity_packet.get("identity_continuity_summary") or {}).get("wake_receipt_present")) else None,
            "record_sleep_summary" if not bool((continuity_packet.get("identity_continuity_summary") or {}).get("sleep_summary_present")) else None,
        ]
    )
    stale_facts = _dedupe_nonempty(
        [
            *(review_handoff_summary.get("refresh_reasons") or []),
            *(continuity_recovery_readiness.get("blocking") or []),
            *(continuity_recovery_readiness.get("cautions") or []),
            *(commitment_summary.get("required_actions") or []),
            continuity_incident_summary.get("latest_event_detail"),
            "continuity_quality_watch" if continuity_quality_summary.get("status") in {"watch", "blocked"} else None,
        ]
    )
    next_action = (
        scheduled_work[0]
        if scheduled_work
        else (
            stale_facts[0]
            if stale_facts
            else "review continuity"
        )
    )

    steering_summary = {
        "agent_id": steering_agent_id,
        "version": steering_version,
        "updated_at": steering_updated_at,
        "changed_since_last_wake": steering_changed_since_last_wake,
        "mode": steering_profile.get("mode"),
        "priority": steering_profile.get("priority"),
        "risk_tolerance": steering_profile.get("risk_tolerance"),
        "leak_mode": steering_profile.get("leak_mode"),
        "private_person_targeting": steering_profile.get("private_person_targeting"),
        "notes": steering_profile.get("notes"),
    } if steering_profile else {}

    narrative_bits: list[str] = []
    if since_last_wake.get("summary"):
        narrative_bits.append(str(since_last_wake.get("summary")))
    if conflicts:
        narrative_bits.append(f"{len(conflicts)} conflict{'' if len(conflicts) == 1 else 's'}")
    if scheduled_work:
        narrative_bits.append(f"{len(scheduled_work)} item{'' if len(scheduled_work) == 1 else 's'} scheduled")
    if steering_changed_since_last_wake and steering_version is not None:
        narrative_bits.append(f"steering v{steering_version} updated")
    if next_action:
        narrative_bits.append(f"next {next_action}")

    return {
        "since_last_wake": since_last_wake or {"summary": "No recent activity.", "counts": {}, "timeline": []},
        "recent_timeline": recent_timeline,
        "conflicts": conflicts,
        "scheduled_work": scheduled_work,
        "stale_facts": stale_facts,
        "next_action": next_action,
        "steering": steering_summary,
        "summary": "; ".join(narrative_bits) if narrative_bits else "No recent continuity changes.",
        "reviewable": bool(conflicts or scheduled_work or steering_changed_since_last_wake),
    }


def _build_self_location_block(
    entity: dict[str, Any],
    *,
    continuity_view: dict[str, Any],
    latest_runs: list[dict[str, Any]],
    action_rationale_summary: dict[str, Any],
    presence_initiative_summary: dict[str, Any],
    review_handoff_summary: dict[str, Any],
) -> dict[str, Any]:
    task_name = _text(entity.get("task_name")) or _text(entity.get("job_id")) or _text(entity.get("id"))
    mode = _text(entity.get("mode")) or _text(entity.get("platform"))
    session_target = _text(entity.get("session_target"))
    operational_session_target = _text(entity.get("operational_session_target"))
    branch_scope = "branch-local" if operational_session_target and operational_session_target != session_target else "shared"

    last_wake_at = _summary_text((entity.get("identity_continuity_summary") or {}).get("last_wake_at"))
    last_activity_at = _summary_text(entity.get("last_activity") or (latest_runs[0].get("started_at") if latest_runs else None))
    freshness_state = "unknown"
    if last_activity_at and last_wake_at:
        freshness_state = "current" if _as_epoch(last_activity_at) >= _as_epoch(last_wake_at) else "stale"
    elif last_activity_at:
        freshness_state = "current"

    goals = _dedupe_nonempty([
        action_rationale_summary.get("current_goal"),
        (review_handoff_summary.get("latest") or {}).get("resolution_context", {}).get("goal")
        if isinstance(review_handoff_summary.get("latest"), dict)
        and isinstance((review_handoff_summary.get("latest") or {}).get("resolution_context"), dict)
        else None,
    ])
    blockers = _dedupe_nonempty(
        [
            *(continuity_view.get("conflicts") or []),
            *(review_handoff_summary.get("release_blockers") or []),
            *(presence_initiative_summary.get("incident_points") or []),
        ]
    )

    memory_scope = {
        "scope": branch_scope,
        "shared_session_target": session_target,
        "branch_session_target": operational_session_target,
        "promotion_rule": (
            "Shared state stays on the shared session target; branch-local state stays on the operational session target until reviewed."
            if operational_session_target
            else "Shared state only."
        ),
    }

    freshness = {
        "last_wake_at": last_wake_at,
        "last_activity_at": last_activity_at,
        "next_earliest_wake_at": _summary_text(presence_initiative_summary.get("next_earliest_wake_at")),
        "freshness_state": freshness_state,
    }

    summary_bits = [part for part in [task_name, mode, goals[0] if goals else None, freshness_state, branch_scope] if part]

    status = "healthy" if task_name and mode and (goals or last_activity_at or last_wake_at) else ("partial" if task_name or mode else "missing")
    return {
        "status": status,
        "role": task_name or entity.get("id"),
        "mode": mode,
        "goals": goals,
        "blockers": blockers,
        "freshness": freshness,
        "active_branch_state": {
            "task_name": task_name,
            "session_target": session_target,
            "operational_session_target": operational_session_target,
            "scope": branch_scope,
        },
        "memory_scope": memory_scope,
        "summary": "; ".join(summary_bits) if summary_bits else "No clear self-location yet.",
        "reviewable": bool(blockers or branch_scope == "branch-local" or goals),
    }


def _build_same_fingerprint_summary(entity: dict[str, Any]) -> dict[str, Any]:
    fingerprint_id = _text(entity.get("fingerprint_id"))
    if not fingerprint_id:
        return {
            "status": "missing",
            "decision": "not_applicable",
            "summary": "No fingerprint identified.",
            "user_visible": False,
        }
    return {
        "status": "hidden",
        "decision": "cut_from_user_visible_claims",
        "summary": "No user-visible same-fingerprint merge/reconciliation path is shipped.",
        "fingerprint_id": fingerprint_id,
        "operational_agent_id": _text(entity.get("operational_agent_id")),
        "user_visible": False,
    }


def build_entity_profile(entity: dict[str, Any], recent_runs: list[dict[str, Any]] | None = None, limit: int = 3) -> dict[str, Any]:
    entity_tokens = _candidate_tokens(entity)
    runs_source = [dict(row) for row in (recent_runs or []) if isinstance(row, dict)]
    runs_source.sort(key=lambda row: _as_epoch(row.get("started_at")), reverse=True)
    latest_runs: list[dict[str, Any]] = []
    for row in runs_source:
        if not _run_matches(entity_tokens, row):
            continue
        latest_runs.append(_summarize_run(row))
        if len(latest_runs) >= max(1, min(limit, 10)):
            break

    memory_health = entity.get("memory_health") if isinstance(entity.get("memory_health"), dict) else {}
    self_model_summary = entity.get("self_model_summary") if isinstance(entity.get("self_model_summary"), dict) else {}
    relationship_memory_summary = (
        entity.get("relationship_memory_summary") if isinstance(entity.get("relationship_memory_summary"), dict) else {}
    )
    confidence_summary = entity.get("confidence_summary") if isinstance(entity.get("confidence_summary"), dict) else {}
    drift_review_summary = entity.get("drift_review_summary") if isinstance(entity.get("drift_review_summary"), dict) else {}
    continuity_recovery_readiness = (
        entity.get("continuity_recovery_readiness") if isinstance(entity.get("continuity_recovery_readiness"), dict) else {}
    )
    continuity_quality_summary = entity.get("continuity_quality_summary") if isinstance(entity.get("continuity_quality_summary"), dict) else {}
    review_handoff_summary = entity.get("review_handoff_summary") if isinstance(entity.get("review_handoff_summary"), dict) else {}
    commitment_summary = entity.get("commitment_summary") if isinstance(entity.get("commitment_summary"), dict) else {}
    continuity_packet = {
        "identity_continuity_summary": entity.get("identity_continuity_summary") if isinstance(entity.get("identity_continuity_summary"), dict) else {},
        "continuity_incident_summary": entity.get("continuity_incident_summary") if isinstance(entity.get("continuity_incident_summary"), dict) else {},
        "continuity_recovery_readiness": continuity_recovery_readiness,
        "continuity_repair_plan": entity.get("continuity_repair_plan") if isinstance(entity.get("continuity_repair_plan"), dict) else {},
        "continuity_repair_observation": entity.get("continuity_repair_observation") if isinstance(entity.get("continuity_repair_observation"), dict) else {},
        "continuity_recovery_ack": entity.get("continuity_recovery_ack") if isinstance(entity.get("continuity_recovery_ack"), dict) else {},
        "post_rebuild_continuity_check": entity.get("post_rebuild_continuity_check") if isinstance(entity.get("post_rebuild_continuity_check"), dict) else {},
        "identity_restore_validation": entity.get("identity_restore_validation") if isinstance(entity.get("identity_restore_validation"), dict) else {},
        "identity_resume_procedure": entity.get("identity_resume_procedure") if isinstance(entity.get("identity_resume_procedure"), dict) else {},
        "identity_resume_observation": entity.get("identity_resume_observation") if isinstance(entity.get("identity_resume_observation"), dict) else {},
        "identity_resume_closeout": entity.get("identity_resume_closeout") if isinstance(entity.get("identity_resume_closeout"), dict) else {},
        "operational_resume_governance_summary": entity.get("operational_resume_governance_summary") if isinstance(entity.get("operational_resume_governance_summary"), dict) else {},
        "operational_resume_checkpoint": entity.get("operational_resume_checkpoint") if isinstance(entity.get("operational_resume_checkpoint"), dict) else {},
        "supervised_resume_validation": entity.get("supervised_resume_validation") if isinstance(entity.get("supervised_resume_validation"), dict) else {},
        "mimicry_control_summary": entity.get("mimicry_control_summary") if isinstance(entity.get("mimicry_control_summary"), dict) else {},
        "voice_belief_separation_summary": entity.get("voice_belief_separation_summary") if isinstance(entity.get("voice_belief_separation_summary"), dict) else {},
        "continuity_quality_summary": entity.get("continuity_quality_summary") if isinstance(entity.get("continuity_quality_summary"), dict) else {},
    }
    continuity_view = _build_continuity_view(
        entity,
        continuity_packet=continuity_packet,
        latest_runs=latest_runs,
        review_handoff_summary=review_handoff_summary,
        commitment_summary=commitment_summary,
    )
    self_location = _build_self_location_block(
        entity,
        continuity_view=continuity_view,
        latest_runs=latest_runs,
        action_rationale_summary=entity.get("action_rationale_summary") if isinstance(entity.get("action_rationale_summary"), dict) else {},
        presence_initiative_summary=entity.get("presence_initiative_summary") if isinstance(entity.get("presence_initiative_summary"), dict) else {},
        review_handoff_summary=review_handoff_summary,
    )
    same_fingerprint_summary = _build_same_fingerprint_summary(entity)
    if drift_review_summary.get("status") in {"watch", "blocked"}:
        continuity_view["summary"] = f"{continuity_view['summary']}; drift {drift_review_summary.get('status')}"
        continuity_view["reviewable"] = True
    if continuity_quality_summary:
        continuity_view["quality"] = continuity_quality_summary
        if continuity_quality_summary.get("status") in {"watch", "blocked"}:
            continuity_view["summary"] = f"{continuity_view['summary']}; continuity quality {continuity_quality_summary.get('status')}"
            continuity_view["reviewable"] = True
    continuity_packet_v2 = {
        "changes": continuity_view.get("since_last_wake"),
        "commitments": commitment_summary,
        "approvals": review_handoff_summary,
        "runs": latest_runs,
        "reflections": {
            "status": "proxy" if latest_runs else "empty",
            "latest_run_id": latest_runs[0]["run_id"] if latest_runs else None,
            "latest_run_status": latest_runs[0]["status"] if latest_runs else None,
        },
        "conflicts": continuity_view.get("conflicts") or [],
        "stale_facts": continuity_view.get("stale_facts") or [],
        "next_action": continuity_view.get("next_action"),
    }
    profile = {
        "overview": {
            "entity_id": entity.get("id"),
            "display_name": entity.get("display_name") or entity.get("id"),
            "platform": entity.get("platform"),
            "mode": entity.get("mode"),
            "task_name": entity.get("task_name"),
            "session_target": entity.get("session_target"),
            "operational_session_target": entity.get("operational_session_target"),
            "operational_agent_id": entity.get("operational_agent_id"),
            "fingerprint_id": entity.get("fingerprint_id"),
            "latest_activity": entity.get("last_activity"),
            "latest_run_count": len(latest_runs),
            "latest_run_id": latest_runs[0]["run_id"] if latest_runs else None,
            "latest_run_status": latest_runs[0]["status"] if latest_runs else None,
            "latest_run_started_at": latest_runs[0]["started_at"] if latest_runs else None,
            "pending_approvals": entity.get("pending_approvals") or review_handoff_summary.get("pending_count") or 0,
            "decisions_count": entity.get("decisions_count") or 0,
        },
        "memory": {
            "status": memory_health.get("status") or "unknown",
            "memory_health": memory_health,
            "self_model_summary": self_model_summary,
            "relationship_memory_summary": relationship_memory_summary,
            "confidence_summary": confidence_summary,
            "mimicry_control_summary": entity.get("mimicry_control_summary") if isinstance(entity.get("mimicry_control_summary"), dict) else {},
            "voice_belief_separation_summary": entity.get("voice_belief_separation_summary") if isinstance(entity.get("voice_belief_separation_summary"), dict) else {},
        },
        "drift_review_summary": drift_review_summary,
        "continuity_quality_summary": continuity_quality_summary,
        "continuity": continuity_packet,
        "continuity_view": continuity_view,
        "continuity_packet_v2": continuity_packet_v2,
        "self_location": self_location,
        "same_fingerprint_summary": same_fingerprint_summary,
        "approvals": {
            "review_handoff_summary": review_handoff_summary,
            "commitment_summary": commitment_summary,
            "agency_control_summary": entity.get("agency_control_summary") if isinstance(entity.get("agency_control_summary"), dict) else {},
            "pending_approvals": entity.get("pending_approvals") or review_handoff_summary.get("pending_count") or 0,
            "decisions_count": entity.get("decisions_count") or 0,
        },
        "latest_runs": latest_runs,
        "reflection_status": {
            "status": "proxy" if latest_runs else "empty",
            "source": "latest_runs" if latest_runs else "none",
            "summary": "Reflection artifacts are not first-class yet; latest runs are the current signal." if latest_runs else "No recent runs found.",
            "latest_run_id": latest_runs[0]["run_id"] if latest_runs else None,
            "latest_run_status": latest_runs[0]["status"] if latest_runs else None,
        },
    }
    return profile
