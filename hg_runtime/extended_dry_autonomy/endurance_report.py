"""Extended dry autonomy endurance report."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.extended_dry_autonomy.endurance_budget import EnduranceBudgetState
from hg_runtime.extended_dry_autonomy.schema import (
    ExtendedDryAutonomyConfig,
    ExtendedDryAutonomyRun,
    LifecycleAnchorAudit,
    ReadinessVerdict,
    now_iso,
)
from hg_runtime.extended_dry_autonomy.storage import run_dir, write_json

WORKSPACE = Path(__file__).resolve().parents[2]
REPORT_PATH = WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_14_ENDURANCE_REPORT.md"


def build_endurance_report(
    *,
    run: ExtendedDryAutonomyRun,
    config: ExtendedDryAutonomyConfig,
    postflight: dict,
    anchor_audit: LifecycleAnchorAudit,
    budget: EnduranceBudgetState,
    duration_seconds: float,
    provider_status: str,
    live_read_status: str,
    readiness: ReadinessVerdict,
    extended_base: Path | None = None,
) -> dict:
    payload = {
        "run_id": run.run_id,
        "agent_id": run.agent_id,
        "duration_seconds": duration_seconds,
        "iteration_count": run.iteration_count,
        "provider_status": provider_status,
        "live_read_status": live_read_status,
        "replay_verdict": postflight.get("replay_verdict"),
        "checkpoint_refs": run.checkpoint_refs,
        "pause_resume_events": run.pause_resume_events,
        "boot_anchor_ref": run.boot_anchor_ref,
        "shutdown_anchor_ref": run.shutdown_anchor_ref,
        "anchor_audit_verdict": anchor_audit.verdict,
        "remote_push_attempted": anchor_audit.remote_push_attempted,
        "remote_freshness_verified": anchor_audit.remote_freshness_verified,
        "endurance_budget": budget.to_payload(),
        "loop_verdict": run.verdict.value,
        "readiness_verdict": readiness.value,
        "external_side_effects": postflight.get("external_side_effects", False),
        "created_at": now_iso(),
    }
    write_json(run_dir(run.run_id, base=extended_base) / "endurance_report.json", payload)
    persist_endurance_report(payload, run=run, config=config, postflight=postflight, anchor_audit=anchor_audit)
    return payload


def persist_endurance_report(
    payload: dict,
    *,
    run: ExtendedDryAutonomyRun,
    config: ExtendedDryAutonomyConfig,
    postflight: dict,
    anchor_audit: LifecycleAnchorAudit,
) -> Path:
    lines = [
        "# Agent Zero Phase 14 Endurance Report",
        "",
        f"**Run ID:** {run.run_id}",
        f"**Agent ID:** {run.agent_id}",
        f"**Verdict:** {run.verdict.value}",
        f"**Readiness:** {payload.get('readiness_verdict')}",
        "",
        "## Run identity",
        f"- Started: {run.started_at}",
        f"- Finished: {run.finished_at}",
        f"- Iterations: {run.iteration_count} / {config.max_iterations}",
        "",
        "## Duration",
        f"- Elapsed: {payload.get('duration_seconds', 0):.1f}s (max {config.max_duration_seconds}s)",
        "",
        "## Provider / live read",
        f"- Provider: {payload.get('provider_status')}",
        f"- Live read: {payload.get('live_read_status')}",
        "",
        "## Receipt / journal / replay",
        f"- Replay: {postflight.get('replay_verdict')}",
        f"- Turn receipts: {len(run.turn_result_refs)}",
        "",
        "## Checkpoint / pause",
        f"- Checkpoints: {len(run.checkpoint_refs)}",
        f"- Pause/resume events: {len(run.pause_resume_events)}",
        "",
        "## Lifecycle anchors",
        f"- Boot: {run.boot_anchor_ref}",
        f"- Shutdown: {run.shutdown_anchor_ref}",
        f"- Anchor audit: {anchor_audit.verdict}",
        f"- Remote push attempted: {anchor_audit.remote_push_attempted}",
        f"- Remote freshness verified: {anchor_audit.remote_freshness_verified}",
        "",
        "## Endurance budget",
        f"- Budget verdict: {payload.get('endurance_budget', {}).get('verdict')}",
        "",
        "## External side effects",
        f"- External side effects: {postflight.get('external_side_effects', False)}",
        f"- Live writes: {postflight.get('live_writes', False)}",
        "",
        f"Generated: {payload.get('created_at')}",
    ]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT_PATH


__all__ = ["build_endurance_report", "persist_endurance_report"]
