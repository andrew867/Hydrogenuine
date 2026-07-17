"""Dry autonomous loop readiness report."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.dry_autonomous_loop.schema import (
    DryAutonomousLoopReadiness,
    DryAutonomousLoopRun,
    DryAutonomousLoopVerdict,
    ReadinessVerdict,
    now_iso,
)
from hg_runtime.dry_autonomous_loop.storage import run_loop_dir, write_json

WORKSPACE = Path(__file__).resolve().parents[2]
READINESS_PATH = WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_13_READINESS_REPORT.md"


def compute_readiness(
    *,
    loop_verdict: DryAutonomousLoopVerdict,
    provider_status: str,
    live_read_status: str,
    duration_seconds: float,
    max_duration_seconds: int,
    external_side_effects: bool,
) -> ReadinessVerdict:
    if loop_verdict.value.startswith("RED_") or external_side_effects:
        return ReadinessVerdict.RED_NOT_READY_FOR_PHASE_14
    if provider_status == "unavailable" or live_read_status == "unavailable":
        return ReadinessVerdict.YELLOW_READY_WITH_PROVIDER_OR_CREDENTIAL_LIMITS
    if duration_seconds < max_duration_seconds * 0.5:
        return ReadinessVerdict.YELLOW_READY_ONLY_FOR_SHORT_BOUNDED_DRY_RUNS
    if loop_verdict == DryAutonomousLoopVerdict.GREEN_DRY_AUTONOMOUS_LOOP_COMPLETE:
        return ReadinessVerdict.GREEN_READY_FOR_PHASE_14_EXTENDED_DRY_AUTONOMY
    return ReadinessVerdict.YELLOW_READY_WITH_PROVIDER_OR_CREDENTIAL_LIMITS


def build_readiness_report(
    *,
    run: DryAutonomousLoopRun,
    duration_seconds: float,
    provider_status: str,
    live_read_status: str,
    external_side_effects: bool,
    max_duration_seconds: int,
) -> DryAutonomousLoopReadiness:
    readiness = compute_readiness(
        loop_verdict=run.verdict,
        provider_status=provider_status,
        live_read_status=live_read_status,
        duration_seconds=duration_seconds,
        max_duration_seconds=max_duration_seconds,
        external_side_effects=external_side_effects,
    )
    return DryAutonomousLoopReadiness(
        run_id=run.run_id,
        loop_verdict=run.verdict.value,
        readiness_verdict=readiness,
        provider_status=provider_status,
        live_read_status=live_read_status,
        duration_seconds=duration_seconds,
        iteration_count=run.iteration_count,
        created_at=now_iso(),
    ).with_hash()


def write_readiness_md(report: DryAutonomousLoopReadiness, *, run: DryAutonomousLoopRun) -> Path:
    lines = [
        "# Phase 13 Readiness Report",
        "",
        f"- run_id: `{report.run_id}`",
        f"- iteration_count: {report.iteration_count}",
        f"- duration_seconds: {report.duration_seconds:.1f}",
        f"- provider_status: `{report.provider_status}`",
        f"- live_read_status: `{report.live_read_status}`",
        f"- loop_verdict: `{report.loop_verdict}`",
        f"- readiness_verdict: `{report.readiness_verdict.value}`",
        f"- boot_anchor_ref: `{run.boot_anchor_ref}`",
        f"- shutdown_anchor_ref: `{run.shutdown_anchor_ref}`",
        "",
    ]
    READINESS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return READINESS_PATH


def persist_readiness(report: DryAutonomousLoopReadiness, *, run_id: str, base: Path | None = None) -> Path:
    return write_json(run_loop_dir(run_id, base=base) / "readiness_report.json", report.to_payload())


__all__ = [
    "build_readiness_report",
    "compute_readiness",
    "persist_readiness",
    "write_readiness_md",
]
