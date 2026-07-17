"""Dry soak readiness report generation."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.dry_soak.schema import (
    DrySoakReadinessReport,
    DrySoakRun,
    DrySoakVerdict,
    ReadinessVerdict,
    now_iso,
)
from hg_runtime.dry_soak.storage import dry_soak_root, write_json

WORKSPACE = Path(__file__).resolve().parents[2]
READINESS_REPORT_PATH = WORKSPACE / "docs/reports/phases/AUTONOMOUS_AGENT_ZERO_PHASE_12_READINESS_REPORT.md"


def compute_readiness_verdict(
    *,
    dry_soak_verdict: DrySoakVerdict,
    provider_status: str,
    live_read_status: str,
    duration_seconds: float,
    target_duration_seconds: int,
    external_side_effects: bool,
) -> ReadinessVerdict:
    if dry_soak_verdict.value.startswith("RED_") or external_side_effects:
        return ReadinessVerdict.RED_NOT_READY_FOR_PHASE_13
    if dry_soak_verdict in (
        DrySoakVerdict.YELLOW_DRY_SOAK_COMPLETED_WITH_PROVIDER_UNAVAILABLE,
        DrySoakVerdict.YELLOW_DRY_SOAK_NO_ARTIFACTS_CREATED,
    ) or provider_status == "unavailable":
        return ReadinessVerdict.YELLOW_READY_WITH_PROVIDER_OR_CREDENTIAL_LIMITS
    if live_read_status == "unavailable":
        return ReadinessVerdict.YELLOW_READY_WITH_PROVIDER_OR_CREDENTIAL_LIMITS
    if duration_seconds < target_duration_seconds * 0.5:
        return ReadinessVerdict.YELLOW_READY_WITH_SHORT_DURATION_ONLY
    if dry_soak_verdict == DrySoakVerdict.GREEN_DRY_SOAK_COMPLETE:
        return ReadinessVerdict.GREEN_READY_FOR_PHASE_13_DRY_AUTONOMOUS_LOOP_PLANNING
    return ReadinessVerdict.YELLOW_READY_WITH_PROVIDER_OR_CREDENTIAL_LIMITS


def build_readiness_report(
    *,
    run: DrySoakRun,
    duration_seconds: float,
    provider_status: str,
    live_read_status: str,
    replay_status: str,
    artifact_count: int,
    review_queue_count: int,
    duplication_verdict: str,
    resource_verdict: str,
    failure_budget_verdict: str,
    external_side_effects: bool,
    target_duration_seconds: int,
    exciton_status: str = "not_checked",
) -> DrySoakReadinessReport:
    readiness = compute_readiness_verdict(
        dry_soak_verdict=run.verdict,
        provider_status=provider_status,
        live_read_status=live_read_status,
        duration_seconds=duration_seconds,
        target_duration_seconds=target_duration_seconds,
        external_side_effects=external_side_effects,
    )
    return DrySoakReadinessReport(
        run_id=run.run_id,
        duration_seconds=duration_seconds,
        turn_count=run.turn_count,
        provider_status=provider_status,
        live_read_status=live_read_status,
        replay_status=replay_status,
        artifact_count=artifact_count,
        review_queue_count=review_queue_count,
        duplication_verdict=duplication_verdict,
        resource_verdict=resource_verdict,
        failure_budget_verdict=failure_budget_verdict,
        external_side_effects=external_side_effects,
        dry_soak_verdict=run.verdict.value,
        readiness_verdict=readiness,
        created_at=now_iso(),
    ).with_hash()


def write_readiness_report_md(
    report: DrySoakReadinessReport,
    *,
    run: DrySoakRun,
    exciton_status: str = "honest_if_implemented",
    stop_panic_status: str = "available",
) -> Path:
    lines = [
        "# Phase 12 Readiness Report",
        "",
        "## 1. Run identity",
        f"- run_id: `{report.run_id}`",
        f"- agent_id: `{run.agent_id}`",
        f"- status: `{run.status.value}`",
        "",
        "## 2. Duration",
        f"- duration_seconds: {report.duration_seconds:.1f}",
        "",
        "## 3. Turn count",
        f"- turn_count: {report.turn_count}",
        "",
        "## 4. Provider status",
        f"- provider_status: `{report.provider_status}`",
        "",
        "## 5. Live read status",
        f"- live_read_status: `{report.live_read_status}`",
        "",
        "## 6. Receipts/journal/replay",
        f"- replay_status: `{report.replay_status}`",
        "",
        "## 7. Artifact/review queue",
        f"- artifact_count: {report.artifact_count}",
        f"- review_queue_count: {report.review_queue_count}",
        "",
        "## 8. Duplication watchdog",
        f"- verdict: `{report.duplication_verdict}`",
        "",
        "## 9. Resource watchdog",
        f"- verdict: `{report.resource_verdict}`",
        "",
        "## 10. STOP/PANIC",
        f"- status: `{stop_panic_status}`",
        "",
        "## 11. EXCITON visibility",
        f"- status: `{exciton_status}`",
        "",
        "## 12. External side effect audit",
        f"- external_side_effects: `{report.external_side_effects}`",
        "",
        "## 13. Failure budget",
        f"- verdict: `{report.failure_budget_verdict}`",
        "",
        "## 14. Summary",
        f"- dry_soak_verdict: `{report.dry_soak_verdict}`",
        f"- readiness_verdict: `{report.readiness_verdict.value}`",
        "",
        "## 15. Phase 13 readiness",
        f"- `{report.readiness_verdict.value}`",
        "",
    ]
    READINESS_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return READINESS_REPORT_PATH


def persist_readiness_report(
    report: DrySoakReadinessReport,
    *,
    run_id: str,
    base: Path | None = None,
) -> Path:
    path = run_dry_soak_dir(run_id, base=base) / "readiness_report.json"
    return write_json(path, report.to_payload())


from hg_runtime.dry_soak.storage import run_dry_soak_dir  # noqa: E402

__all__ = [
    "build_readiness_report",
    "compute_readiness_verdict",
    "persist_readiness_report",
    "write_readiness_report_md",
]
