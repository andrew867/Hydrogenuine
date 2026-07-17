"""EXCITON Phase 0 status aggregator — builds the read-only ExcitonStatusSnapshot.

The aggregator runs the data-source collectors, assembles a snapshot, verifies every
required panel is present, computes an honest overall verdict (degraded panels yield an
allowed YELLOW, never fake-green), and stamps the frozen advisory constants + hash. It
authorizes nothing and executes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from hg_runtime.exciton.data_sources import CollectorContext, build_panels
from hg_runtime.exciton.phase1_data_sources import build_phase1_panels
from hg_runtime.exciton.phase2_data_sources import build_phase2_panels
from hg_runtime.exciton.phase3_data_sources import build_phase3_panels
from hg_runtime.exciton.situational_data_sources import build_situational_panels
from hg_runtime.exciton.watchtower_data_sources import build_inference_watchtower_panels
from hg_runtime.exciton.agent_zero_extended_dry_autonomy_data_sources import build_agent_zero_extended_dry_autonomy_panels
from hg_runtime.exciton.agent_zero_provider_monitor_data_sources import build_agent_zero_provider_monitor_panels
from hg_runtime.exciton.agent_zero_live_read_monitor_data_sources import build_agent_zero_live_read_monitor_panels
from hg_runtime.exciton.agent_zero_external_write_authority_data_sources import build_agent_zero_external_write_authority_panels
from hg_runtime.exciton.agent_zero_phase18_live_smoke_data_sources import build_agent_zero_phase18_live_smoke_panels
from hg_runtime.exciton.agent_zero_phase19_incident_data_sources import build_agent_zero_phase19_incident_panels
from hg_runtime.exciton.agent_zero_task_selection_data_sources import build_agent_zero_task_selection_panels
from hg_runtime.exciton.agent_zero_hands_off_session_data_sources import build_agent_zero_hands_off_session_panels
from hg_runtime.exciton.agent_zero_governed_work_loop_data_sources import build_agent_zero_governed_work_loop_panels
from hg_runtime.exciton.agent_zero_overnight_field_run_data_sources import build_agent_zero_overnight_field_run_panels
from hg_runtime.exciton.agent_zero_real_soak_launch_data_sources import build_agent_zero_real_soak_launch_panels
from hg_runtime.exciton.agent_zero_dry_autonomous_loop_data_sources import build_agent_zero_dry_autonomous_loop_panels
from hg_runtime.exciton.agent_zero_dry_soak_data_sources import build_agent_zero_dry_soak_panels
from hg_runtime.exciton.agent_zero_rehearsal_data_sources import build_agent_zero_rehearsal_panels
from hg_runtime.exciton.agent_zero_review_data_sources import build_agent_zero_review_panels
from hg_runtime.exciton.agent_zero_console_data_sources import build_agent_zero_console_panels
from hg_runtime.exciton.panel_registry import missing_required_panels
from hg_runtime.exciton.schema import (
    FIXTURE_UTC,
    ExcitonPanelState,
    ExcitonRefreshPolicy,
    ExcitonStatusSnapshot,
    new_id,
)


@dataclass
class AggregatorConfig:
    offline_fixture: bool = False
    allow_network: bool = False
    refresh_interval_seconds: float = 15.0


def _now_iso(offline_fixture: bool) -> str:
    if offline_fixture:
        return FIXTURE_UTC
    return datetime.now(timezone.utc).isoformat()


def _overall_verdict(panels) -> tuple[str, list[str]]:
    warnings: list[str] = []
    has_red = any(p.state == ExcitonPanelState.RED for p in panels)
    degraded = [p.panel_id for p in panels if p.state in (ExcitonPanelState.DEGRADED, ExcitonPanelState.UNKNOWN)]
    yellow = [p.panel_id for p in panels if p.state == ExcitonPanelState.YELLOW]
    if has_red:
        return "RED_EXCITON_STATUS_BREACH", warnings
    if degraded:
        warnings.append("YELLOW_OPTIONAL_PANEL_DEGRADED")
        if "AudioPanel" in degraded:
            warnings.append("YELLOW_PLAYBACK_DISABLED")
        return "YELLOW_OPTIONAL_PANEL_DEGRADED", warnings
    if yellow:
        warnings.append("YELLOW_OPTIONAL_PANEL_DEGRADED")
        return "YELLOW_OPTIONAL_PANEL_DEGRADED", warnings
    return "GREEN_EXCITON_STATUS_OK", warnings


def build_snapshot(config: AggregatorConfig | None = None) -> ExcitonStatusSnapshot:
    config = config or AggregatorConfig()
    ctx = CollectorContext(offline_fixture=config.offline_fixture, allow_network=config.allow_network)
    panels = build_panels(ctx) + build_phase1_panels(ctx)
    panels += build_phase2_panels(ctx, prior_panels=panels)
    panels += build_phase3_panels(ctx)
    panels += build_situational_panels(
        generated_at=_now_iso(config.offline_fixture), offline_fixture=config.offline_fixture
    )
    panels += build_inference_watchtower_panels(ctx)
    panels += build_agent_zero_console_panels(ctx)
    panels += build_agent_zero_review_panels(ctx)
    panels += build_agent_zero_rehearsal_panels(ctx)
    panels += build_agent_zero_dry_soak_panels(ctx)
    panels += build_agent_zero_dry_autonomous_loop_panels(ctx)
    panels += build_agent_zero_extended_dry_autonomy_panels(ctx)
    panels += build_agent_zero_provider_monitor_panels(ctx)
    panels += build_agent_zero_live_read_monitor_panels(ctx)
    panels += build_agent_zero_external_write_authority_panels(ctx)
    panels += build_agent_zero_phase18_live_smoke_panels(ctx)
    panels += build_agent_zero_phase19_incident_panels(ctx)
    panels += build_agent_zero_task_selection_panels(ctx)
    panels += build_agent_zero_hands_off_session_panels(ctx)
    panels += build_agent_zero_governed_work_loop_panels(ctx)
    panels += build_agent_zero_overnight_field_run_panels(ctx)
    panels += build_agent_zero_real_soak_launch_panels(ctx)

    if config.offline_fixture:
        for p in panels:
            p.fields["data_tier"] = "FIXTURE"

    missing = missing_required_panels([p.panel_id for p in panels])
    if missing:
        # Structural failure — surface it rather than hide it.
        raise RuntimeError(f"RED_EXCITON_MISSING_PANEL: {missing}")

    overall, warnings = _overall_verdict(panels)

    temporal = next((p for p in panels if p.panel_id == "TemporalPanel"), None)
    chrono_ref = temporal.fields.get("chrono_ref") if temporal else None

    snapshot = ExcitonStatusSnapshot(
        snapshot_id="exciton-fixture-snapshot" if config.offline_fixture else new_id("snap"),
        generated_at=_now_iso(config.offline_fixture),
        chrono_ref=chrono_ref,
        overall_verdict=overall,
        panels=panels,
        refresh_policy=ExcitonRefreshPolicy(interval_seconds=config.refresh_interval_seconds),
        dangerous_actions_disabled=True,
        stop_available=True,
        panic_available=True,
        warnings=warnings,
    )
    return snapshot


__all__ = ["AggregatorConfig", "build_snapshot"]
