"""EXCITON Phase 3 human-readable activity view — display only, no authority."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.exciton.live_activity import build_live_activity
from hg_runtime.exciton.night_watch import build_night_watch
from hg_runtime.exciton.soak_watchtower import build_soak_watchtower
from hg_runtime.operator_action_queue.filters import pending_items
from hg_runtime.operator_action_queue.queue import open_default_queue
from hg_runtime.operator_action_queue.stop_panic_policy import load_stop_panic_state

WORKSPACE = Path(__file__).resolve().parents[2]

HUMAN_STATES = frozenset(
    {
        "Idle",
        "Waking",
        "Checking status",
        "Reading source",
        "Treating source as cargo",
        "Drafting",
        "Waiting for review",
        "Applying auto-approval rule",
        "Rate-limited",
        "Publishing approved item",
        "Writing receipt",
        "Sleeping until next cycle",
        "Stopped",
        "Panic",
    }
)

HEADLINES = {
    "Idle": "Zero is idle.",
    "Waking": "Zero is checking status.",
    "Checking status": "Zero is checking status.",
    "Reading source": "Zero is reading source material.",
    "Treating source as cargo": "Zero treated source content as cargo.",
    "Drafting": "Zero is drafting.",
    "Waiting for review": "Zero is waiting for operator review.",
    "Applying auto-approval rule": "Zero is applying a scoped auto-approval rule.",
    "Rate-limited": "Zero is rate-limited.",
    "Publishing approved item": "Zero is publishing an approved item.",
    "Writing receipt": "Zero is writing a receipt.",
    "Sleeping until next cycle": "Zero is sleeping until the next cycle.",
    "Stopped": "Zero is stopped.",
    "Panic": "Zero is in panic stop.",
}


def _stop_panic_label(state) -> str:
    if state.panic_active:
        return "panic"
    if state.stop_active:
        return "stopped"
    if state.emergency_lock:
        return "stopping"
    return "clear"


def _infer_state(
    *,
    stop_panic,
    pending: int,
    soak: dict,
    live: dict,
) -> str:
    if stop_panic.panic_active:
        return "Panic"
    if stop_panic.stop_active or stop_panic.emergency_lock:
        return "Stopped"
    task = str(live.get("current_task") or "").lower()
    loop = str(live.get("current_loop_state") or "").lower()
    if "rate" in loop or "rate" in task:
        return "Rate-limited"
    if pending > 0:
        return "Waiting for review"
    if "draft" in task:
        return "Drafting"
    if "read" in task or "source" in task:
        return "Reading source"
    if "cargo" in task:
        return "Treating source as cargo"
    if "receipt" in task or live.get("last_receipt_hash"):
        return "Writing receipt"
    if soak.get("active") and soak.get("publish_enabled"):
        return "Publishing approved item"
    if soak.get("active"):
        return "Sleeping until next cycle"
    if loop in ("idle", ""):
        return "Idle"
    if "check" in task or "status" in task:
        return "Checking status"
    return "Idle"


def build_activity_view(*, workspace: Path | None = None) -> dict[str, Any]:
    ws = workspace or WORKSPACE
    stop_panic = load_stop_panic_state(ws)
    soak = build_soak_watchtower(workspace=ws)
    live = build_live_activity(workspace=ws)
    night = build_night_watch()
    queue = open_default_queue(ws)
    pending_list = pending_items(queue.list_items())
    pending = len(pending_list)

    state = _infer_state(stop_panic=stop_panic, pending=pending, soak=soak, live=live)
    if state not in HUMAN_STATES:
        state = "Idle"

    last_action = str(live.get("last_output_summary") or "No recent action recorded.")
    current_task = str(live.get("current_task") or "No active task")
    blockers = list(night.get("safe_blockers") or [])
    if pending:
        blockers.append(f"{pending} action(s) awaiting operator review")

    return {
        "schema": "exciton-activity-view",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_mode": "Night Watch" if soak.get("active") else "Idle",
        "current_cycle": soak.get("current_phase") or live.get("current_loop_state") or "—",
        "current_task": current_task,
        "current_state": state,
        "headline": HEADLINES[state],
        "next_wake_cycle": soak.get("next_cycle_eta_seconds"),
        "current_queue_item": (
            pending_list[0].action_request.human_summary[:160]
            if pending_list
            else None
        ),
        "last_action": last_action[:240],
        "last_receipt": live.get("last_receipt_hash"),
        "current_safety_checks": {
            "trust_boundary": live.get("trust_boundary_result", "HELD"),
            "opb": "OK",
            "permit": live.get("permit_decision", "NONE"),
            "rate_limit": soak.get("rate_limit_status", "ok"),
            "observer": soak.get("observer_verdict", night.get("observer_verdict", "unknown")),
            "stop_panic": _stop_panic_label(stop_panic),
        },
        "current_blockers": blockers,
        "draft_count": 0,
        "pending_approvals": pending,
        "observer_heartbeat": soak.get("observer_heartbeat_age_seconds"),
        "stop_panic_state": _stop_panic_label(stop_panic),
        "safe_to_step_away": bool(night.get("safe_to_step_away")),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def activity_view_json(*, workspace: Path | None = None) -> str:
    return json.dumps(build_activity_view(workspace=workspace), indent=2, sort_keys=True)


__all__ = ["HEADLINES", "HUMAN_STATES", "activity_view_json", "build_activity_view"]
