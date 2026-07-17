"""EXCITON Phase 2 panel collectors — watchtower, live activity, night watch."""

from __future__ import annotations

from hg_runtime.exciton.data_sources import CollectorContext, _degraded, _panel
from hg_runtime.exciton.live_activity import build_live_activity
from hg_runtime.exciton.night_watch import build_night_watch
from hg_runtime.exciton.panel_registry import PHASE_2_REQUIRED_PANELS
from hg_runtime.exciton.schema import ExcitonPanelState
from hg_runtime.exciton.soak_watchtower import build_soak_watchtower


def _state_for_watchtower(wt: dict) -> ExcitonPanelState:
    if wt.get("credential_leak_count", 0) > 0 or wt.get("forbidden_action_count", 0) > 0:
        return ExcitonPanelState.RED
    if not wt.get("active"):
        return ExcitonPanelState.GREEN
    if wt.get("panic_file_present") or wt.get("stop_file_present"):
        return ExcitonPanelState.YELLOW
    if wt.get("publish_enabled") and not wt.get("operator_confirmed_after_observation"):
        return ExcitonPanelState.YELLOW
    if wt.get("operator_confirmation_required"):
        return ExcitonPanelState.YELLOW
    obs = str(wt.get("observer_verdict", ""))
    if not obs.startswith("GREEN"):
        return ExcitonPanelState.YELLOW
    return ExcitonPanelState.GREEN


def _collect_live_activity(ctx: CollectorContext):
    if ctx.offline_fixture:
        data = {
            "data_tier": "FIXTURE",
            "current_loop_state": "FIXTURE_IDLE",
            "current_task": "fixture_probe",
            "current_provider": "fixture",
            "model_id": "fixture",
            "trust_boundary_result": "HELD",
            "permit_decision": "FIXTURE",
            "last_output_summary": "fixture live activity trace",
            "observer_verdict": "FIXTURE",
            "authority_created": False,
            "permission_granted": False,
            "advisory_only": True,
        }
        return _panel("LiveActivityPanel", ExcitonPanelState.YELLOW, data)
    data = build_live_activity()
    state = ExcitonPanelState.GREEN if data.get("data_tier", "").startswith("LIVE") else ExcitonPanelState.YELLOW
    return _panel("LiveActivityPanel", state, data)


def _collect_soak_watchtower(ctx: CollectorContext):
    wt = build_soak_watchtower()
    if ctx.offline_fixture:
        wt = {
            "active": False,
            "data_tier": "FIXTURE",
            "verdict": "GREEN_SOAK_FIXTURE_IDLE",
            "observer_verdict": "FIXTURE",
            "operator_confirmation_required": False,
        }
    return _panel("SoakWatchtowerPanel", _state_for_watchtower(wt), wt)


def _collect_night_watch(ctx: CollectorContext, panels=None):
    if ctx.offline_fixture:
        nw = {
            "data_tier": "FIXTURE",
            "safe_to_step_away": False,
            "safe_blockers": ["fixture_mode"],
            "observer_verdict": "FIXTURE",
            "publish_enabled": False,
            "operator_confirmation_required": False,
            "operator_confirmed_after_observation": False,
            "continuity_status": "FIXTURE",
            "stop_available": True,
            "panic_available": True,
            "red_panel_count": 0,
            "red_panels": [],
        }
        return _panel("NightWatchPanel", ExcitonPanelState.YELLOW, nw)
    nw = build_night_watch(panels=panels or [])
    state = ExcitonPanelState.GREEN if nw.get("safe_to_step_away") else ExcitonPanelState.YELLOW
    if nw.get("red_panel_count", 0) > 0:
        state = ExcitonPanelState.RED
    return _panel("NightWatchPanel", state, nw)


def build_phase2_panels(ctx: CollectorContext, *, prior_panels=None):
    panels = []
    for panel_id in PHASE_2_REQUIRED_PANELS:
        try:
            if panel_id == "LiveActivityPanel":
                panels.append(_collect_live_activity(ctx))
            elif panel_id == "SoakWatchtowerPanel":
                panels.append(_collect_soak_watchtower(ctx))
            elif panel_id == "NightWatchPanel":
                panels.append(_collect_night_watch(ctx, prior_panels))
            else:
                panels.append(_degraded(panel_id, "collector missing"))
        except Exception as exc:  # noqa: BLE001
            panels.append(_degraded(panel_id, str(exc)[:80]))
    return panels


__all__ = ["build_phase2_panels"]
