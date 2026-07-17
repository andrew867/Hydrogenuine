"""EXCITON hands-off session monitor snapshot."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.hands_off_session.heartbeat import load_latest_heartbeat
from hg_runtime.hands_off_session.postflight import load_postflight
from hg_runtime.hands_off_session.schema import STORE_ROOT, load_hands_off_policy, now_iso
from hg_runtime.hands_off_session.session_lock import read_lock
from hg_runtime.hands_off_session.session_state import load_state
from hg_runtime.hands_off_session.manual_controls import check_panic, check_stop


def build_hands_off_session_monitor_snapshot(session_id: str | None = None) -> dict[str, Any]:
    policy = load_hands_off_policy()
    lock = read_lock()
    active_session = session_id or (lock.session_id if lock else None)

    state = load_state(active_session) if active_session else None
    hb = load_latest_heartbeat(active_session) if active_session else None
    postflight = load_postflight(active_session) if active_session else None

    stop_active = check_stop(active_session) if active_session else False
    panic_active = check_panic(active_session) if active_session else False

    freshness = hb.created_at if hb else (state.started_at if state else now_iso())
    heartbeat_stale = False
    if hb:
        try:
            ts = datetime.fromisoformat(hb.created_at.replace("Z", "+00:00"))
            heartbeat_stale = (datetime.now(timezone.utc) - ts).total_seconds() > 180
        except Exception:
            heartbeat_stale = True

    verdict = "YELLOW_NO_HANDS_OFF_SESSION"
    if postflight:
        verdict = postflight.verdict
    elif state:
        verdict = f"GREEN_HANDS_OFF_{state.status.upper()}" if state.status == "running" else state.status

    external_green = False
    if heartbeat_stale or not hb or not state:
        external_green = False
    if state and state.status != "running":
        external_green = False

    return {
        "panel_id": "agent_zero_hands_off_session_monitor",
        "title": "Agent Zero Hands-Off Session Monitor",
        "session_id": active_session,
        "pid": state.pid if state else None,
        "foreground_status": state.status if state else "none",
        "scheduler_allowed": False,
        "daemon_allowed": False,
        "service_allowed": False,
        "cron_allowed": False,
        "fixed_turn_cap": None,
        "fixed_duration_cap": None,
        "turn_count": state.turn_count if state else 0,
        "selected_task_count": state.selected_task_count if state else 0,
        "idle_count": state.idle_count if state else 0,
        "last_selected_task": state.last_task_selection_ref if state else None,
        "last_task_receipt": state.last_task_selection_ref if state else None,
        "last_turn_receipt": state.last_turn_ref if state else None,
        "last_broker_decision": state.last_broker_decision_ref if state else None,
        "heartbeat_freshness": freshness,
        "heartbeat_stale": heartbeat_stale,
        "stop_status": "active" if stop_active else "clear",
        "panic_status": "active" if panic_active else "clear",
        "resource_budget": state.resource_budget_status if state else {},
        "failure_budget": state.failure_budget_status if state else {},
        "external_side_effect_count": state.external_side_effect_count if state else 0,
        "verdict": verdict,
        "external_action_autonomous_green": external_green,
        "policy_phase": policy.get("phase", 22),
        "live_writes_allowed": policy.get("live_writes_allowed", False),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
