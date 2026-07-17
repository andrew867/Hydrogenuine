"""EXCITON overnight field run monitor snapshot."""

from __future__ import annotations

from typing import Any

from hg_runtime.overnight_field_run.continuity_audit import load_continuity_audit
from hg_runtime.overnight_field_run.field_run_postflight import load_postflight
from hg_runtime.overnight_field_run.field_run_state import load_state
from hg_runtime.overnight_field_run.schema import FieldRunMode, OvernightFieldRunVerdict, STORE_ROOT
from hg_runtime.overnight_field_run.wake_report import load_wake_report


def build_overnight_field_run_monitor_snapshot(field_run_id: str | None = None) -> dict[str, Any]:
    """Read-only monitor snapshot — no live action buttons."""
    run_id = field_run_id
    if not run_id and STORE_ROOT.is_dir():
        dirs = sorted([p for p in STORE_ROOT.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime)
        if dirs:
            run_id = dirs[-1].name

    state = load_state(run_id) if run_id else None
    postflight = load_postflight(run_id) if run_id else None
    wake = load_wake_report(run_id) if run_id else None
    continuity = load_continuity_audit(run_id) if run_id else None

    verdict = OvernightFieldRunVerdict.YELLOW_FIELD_RUN_NOT_STARTED.value
    if postflight:
        verdict = postflight.verdict
    elif state:
        verdict = "YELLOW_PHASE24_FIELD_RUN_IN_PROGRESS"

    infrastructure_only = postflight.infrastructure_only if postflight else False
    policy = __import__("hg_runtime.overnight_field_run.schema", fromlist=["load_field_run_policy"]).load_field_run_policy()
    min_elapsed = float(policy.get("min_elapsed_seconds_for_overnight_complete", 3600))
    import os

    elapsed_ok = False
    if state and state.started_at and state.stopped_at:
        from datetime import datetime, timezone

        try:
            start_dt = datetime.fromisoformat(state.started_at.replace("Z", "+00:00"))
            stop_dt = datetime.fromisoformat(state.stopped_at.replace("Z", "+00:00"))
            elapsed_ok = (stop_dt - start_dt).total_seconds() >= min_elapsed
        except (ValueError, TypeError):
            elapsed_ok = False

    overnight_green_eligible = (
        postflight is not None
        and postflight.mode == FieldRunMode.OPERATOR_FIELD_RUN.value
        and postflight.turn_count >= 10
        and not postflight.verdict.startswith("RED_")
        and not infrastructure_only
        and elapsed_ok
        and os.environ.get("HG_HANDS_OFF_FAST_TURNS") != "1"
    )

    return {
        "panel_title": "Agent Zero Overnight Field Run Monitor",
        "field_run_id": run_id or "",
        "mode": state.mode if state else "",
        "pid": state.pid if state else None,
        "foreground_status": True,
        "started_at": state.started_at if state else "",
        "turn_count": state.turn_count if state else 0,
        "task_selection_count": state.task_selection_count if state else 0,
        "governed_work_count": state.governed_work_count if state else 0,
        "internal_work_count": state.internal_work_count if state else 0,
        "external_candidate_count": state.external_candidate_count if state else 0,
        "dry_dispatch_count": state.dry_dispatch_count if state else 0,
        "live_dispatch_count": state.live_dispatch_count if state else 0,
        "refusal_count": state.refusal_count if state else 0,
        "idle_count": state.idle_count if state else 0,
        "last_selected_task": state.last_selected_task_type if state else "",
        "last_work_item_ref": state.last_work_item_ref if state else "",
        "last_turn_receipt_ref": state.last_turn_receipt_ref if state else "",
        "last_task_selection_ref": state.last_task_selection_ref if state else "",
        "last_governed_work_ref": state.last_governed_work_ref if state else "",
        "heartbeat_freshness": "fresh" if state and state.last_heartbeat_ref else "unknown",
        "checkpoint_freshness": "fresh" if state and state.last_checkpoint_ref else "unknown",
        "stop_status": state.stop_requested if state else False,
        "panic_status": state.panic_requested if state else False,
        "continuity_audit_status": continuity.verdict if continuity else "pending",
        "wake_report_status": wake.verdict if wake else "pending",
        "external_side_effect_count": state.external_side_effect_count if state else 0,
        "infrastructure_only": infrastructure_only,
        "overnight_green_eligible": overnight_green_eligible,
        "verdict": verdict,
        "live_action_buttons": False,
        "publish_available": False,
    }
