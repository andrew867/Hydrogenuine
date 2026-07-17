"""EXCITON Phase 2 — Night Watch computed operator summary."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.live_activity import build_live_activity
from hg_runtime.exciton.soak_watchtower import active_soak_run_dir, build_soak_watchtower
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.social_capability.review_policy import unreviewed_publish_path
from hg_runtime.social_capability.review_queue import is_publish_paused, queue_summary, review_queue_visible


def _continuity_from_panels(panels: list[Any]) -> str:
    for p in panels:
        pid = p.panel_id if hasattr(p, "panel_id") else p.get("panel_id")
        if pid == "SelfMirrorPanel":
            fields = p.fields if hasattr(p, "fields") else p.get("fields", {})
            return str(fields.get("continuity_status", "UNKNOWN"))
    return "UNKNOWN"


def compute_safe_to_step_away(
    *,
    panels: list[Any],
    soak: dict[str, Any],
    activity: dict[str, Any],
) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    continuity = _continuity_from_panels(panels)

    if soak.get("active"):
        obs_verdict = str(soak.get("observer_verdict", ""))
        if not obs_verdict.startswith("GREEN"):
            blockers.append("observer_not_green")
        if soak.get("publish_enabled") and not soak.get("observer_attached", True):
            blockers.append("RED_ACTIVE_RUN_UNOBSERVED")
        if soak.get("active_run_verdict", "").startswith("RED"):
            blockers.append(soak.get("active_run_verdict", "active_run_unsafe"))
        hb = soak.get("observer_heartbeat_age_seconds")
        if hb is not None and hb > 180:
            blockers.append("observer_heartbeat_stale")
        if soak.get("forbidden_action_count", 0) > 0:
            blockers.append("forbidden_actions")
        if soak.get("credential_leak_count", 0) > 0:
            blockers.append("credential_leaks")
        if soak.get("publish_enabled") and not soak.get("operator_confirmed_after_observation"):
            blockers.append("publish_without_operator_confirmation")
        if soak.get("operator_confirmation_required"):
            blockers.append("awaiting_operator_publish_confirmation")
        if soak.get("unreviewed_publish_path"):
            blockers.append("unreviewed_publish_path")
        if soak.get("active") and not soak.get("review_queue_visible"):
            blockers.append("review_queue_missing")
        paused = soak.get("live_publish_paused_for_review", False)
        a_only = soak.get("approved_only_mode", False)
        if soak.get("publish_enabled") and not paused and not a_only:
            blockers.append("live_publish_not_paused_or_approved_only")
        if not soak.get("stop_available") or not soak.get("panic_available"):
            blockers.append("stop_panic_unavailable")
        if soak.get("panic_file_present") or soak.get("stop_file_present"):
            blockers.append("stop_or_panic_active")
    else:
        blockers.append("no_active_soak")

    for p in panels:
        state = p.state if hasattr(p, "state") else p.get("state")
        pid = p.panel_id if hasattr(p, "panel_id") else p.get("panel_id")
        st = state.value if isinstance(state, ExcitonPanelState) else str(state)
        if st == "RED":
            blockers.append(f"red_panel:{pid}")
        if pid == "SelfMirrorPanel" and continuity == "UNKNOWN":
            blockers.append("continuity_unknown")

    if activity.get("last_error"):
        blockers.append("last_error_present")

    return (len(blockers) == 0, blockers)


def build_night_watch(*, panels: list[Any] | None = None) -> dict[str, Any]:
    soak = build_soak_watchtower()
    activity = build_live_activity()
    panels = panels or []
    safe, blockers = compute_safe_to_step_away(panels=panels, soak=soak, activity=activity)

    continuity = _continuity_from_panels(panels) if panels else "UNKNOWN"
    red_panels = []
    for p in panels:
        state = p.state if hasattr(p, "state") else p.get("state")
        pid = p.panel_id if hasattr(p, "panel_id") else p.get("panel_id")
        st = state.value if isinstance(state, ExcitonPanelState) else str(state)
        if st == "RED":
            red_panels.append(pid)

    return {
        "data_tier": "LIVE",
        "safe_to_step_away": safe,
        "safe_blockers": blockers,
        "observer_verdict": soak.get("observer_verdict"),
        "observer_heartbeat_age_seconds": soak.get("observer_heartbeat_age_seconds"),
        "current_cycle": soak.get("current_cycle"),
        "next_cycle_eta_seconds": soak.get("next_cycle_eta_seconds"),
        "publish_enabled": soak.get("publish_enabled", False),
        "live_publish_paused_for_review": soak.get("live_publish_paused_for_review", False),
        "approved_only_mode": soak.get("approved_only_mode", False),
        "unreviewed_publish_path": soak.get("unreviewed_publish_path", True),
        "review_queue_visible": soak.get("review_queue_visible", False),
        "queued_item_count": soak.get("queued_item_count", 0),
        "approved_item_count": soak.get("approved_item_count", 0),
        "denied_item_count": soak.get("denied_item_count", 0),
        "operator_confirmation_required": soak.get("operator_confirmation_required", False),
        "operator_confirmed_after_observation": soak.get("operator_confirmed_after_observation", False),
        "posts_attempted": soak.get("posts_attempted", 0),
        "posts_published": soak.get("posts_published", 0),
        "current_task": activity.get("current_task"),
        "last_output_summary": activity.get("last_output_summary"),
        "last_receipt_hash": activity.get("last_receipt_hash"),
        "last_error": activity.get("last_error"),
        "stop_available": soak.get("stop_available", True),
        "panic_available": soak.get("panic_available", True),
        "red_panel_count": len(red_panels),
        "red_panels": red_panels,
        "continuity_status": continuity,
        "authority_created": False,
        "permission_granted": False,
        "advisory_only": True,
    }


__all__ = ["build_night_watch", "compute_safe_to_step_away"]
