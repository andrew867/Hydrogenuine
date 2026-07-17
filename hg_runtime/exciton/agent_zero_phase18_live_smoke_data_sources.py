"""EXCITON Phase 18 live smoke monitor — read-only."""

from __future__ import annotations

from typing import Any

from hg_runtime.exciton.data_sources import CollectorContext, _panel
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.external_write_authority.live_smoke import (
    Phase18Verdict,
    get_live_dispatch_count,
    load_phase18_policy,
    phase18_env_configured,
    stop_panic_active,
)
from hg_runtime.external_write_authority.live_smoke import PHASE18_ROOT
import json


def build_phase18_monitor_fields() -> dict[str, Any]:
    policy = load_phase18_policy()
    env = phase18_env_configured()
    dispatch_count = get_live_dispatch_count()

    scope_status = "missing"
    platform = env.get("platform") or None
    action_type = env.get("action_type") or None
    content_hash = env.get("expected_content_sha256") or None
    proof_ref = None
    live_permit_ref = None
    dry_permit_ref = None
    candidate_ref = None
    confirmation_ref = None
    dispatch_status = "not_attempted"
    rollback_plan = None

    scopes_dir = PHASE18_ROOT / "scopes"
    if scopes_dir.is_dir():
        files = sorted(scopes_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            data = json.loads(files[0].read_text(encoding="utf-8"))
            scope_status = data.get("status", "unknown")
            platform = data.get("platform")
            action_type = data.get("action_type")
            content_hash = data.get("content_sha256")

    results_dir = PHASE18_ROOT / "dispatch_results"
    if results_dir.is_dir():
        files = sorted(results_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            data = json.loads(files[0].read_text(encoding="utf-8"))
            dispatch_status = "completed" if data.get("external_side_effect") else "dry_or_blocked"
            proof_ref = data.get("proof_ref")
            live_permit_ref = data.get("live_permit_ref")

    permits_dir = PHASE18_ROOT / "live_permits"
    if permits_dir.is_dir() and not live_permit_ref:
        files = sorted(permits_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            data = json.loads(files[0].read_text(encoding="utf-8"))
            live_permit_ref = data.get("live_permit_id")
            dry_permit_ref = data.get("phase17_permit_ref")
            candidate_ref = data.get("candidate_ref")
            confirmation_ref = data.get("operator_confirmation_ref")

    plans_dir = PHASE18_ROOT / "incident_plans"
    if plans_dir.is_dir():
        files = sorted(plans_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            rollback_plan = json.loads(files[0].read_text(encoding="utf-8")).get("incident_plan_id")

    if dispatch_count > 1:
        verdict = "RED_MULTIPLE_LIVE_ACTIONS"
    elif dispatch_count == 1 and proof_ref:
        verdict = Phase18Verdict.GREEN
    elif dispatch_count == 1:
        verdict = Phase18Verdict.YELLOW_VISIBILITY
    elif env["allow_live_smoke"]:
        verdict = Phase18Verdict.YELLOW_READY
    else:
        verdict = Phase18Verdict.YELLOW_READY

    if stop_panic_active():
        verdict = "RED_STOP_PANIC_ACTIVE"

    return {
        "panel_title": "Agent Zero Phase 18 Live Smoke Monitor",
        "live_scope_status": scope_status,
        "platform": platform,
        "action_type": action_type,
        "content_hash": content_hash,
        "candidate_ref": candidate_ref,
        "dry_permit_ref": dry_permit_ref,
        "live_permit_ref": live_permit_ref,
        "operator_confirmation_ref": confirmation_ref,
        "dispatch_status": dispatch_status,
        "external_side_effect_count": dispatch_count,
        "platform_proof": proof_ref,
        "rollback_plan": rollback_plan,
        "stop_panic_active": stop_panic_active(),
        "dry_run_only_default": not env["allow_live_smoke"],
        "exciton_is_approval": False,
        "live_write_buttons": False,
        "verdict": verdict,
        "truth_state": verdict,
    }


def _build_panel(ctx: CollectorContext) -> Any:
    fields = build_phase18_monitor_fields()
    verdict = fields.get("verdict", Phase18Verdict.YELLOW_READY)
    if str(verdict).startswith("RED_"):
        state = ExcitonPanelState.RED
    elif str(verdict).startswith("GREEN_"):
        state = ExcitonPanelState.GREEN
    else:
        state = ExcitonPanelState.YELLOW
    fields["direct_external_actions_allowed"] = False
    fields["publish_available"] = False
    return _panel("AgentZeroPhase18LiveSmokeMonitorPanel", state, fields)


def build_agent_zero_phase18_live_smoke_panels(ctx: CollectorContext) -> list:
    return [_build_panel(ctx)]


__all__ = ["build_agent_zero_phase18_live_smoke_panels", "build_phase18_monitor_fields"]
