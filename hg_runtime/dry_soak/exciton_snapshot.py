"""EXCITON dry soak monitor snapshot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_runtime.dry_soak.failure_budget import FailureBudgetState
from hg_runtime.dry_soak.schema import DrySoakDuplicationReport, DrySoakResourceSnapshot, now_iso
from hg_runtime.supervised_rehearsal.observer import assess_heartbeat_freshness
from hg_runtime.supervised_rehearsal.run_lock import lock_state, read_lock


def build_exciton_dry_soak_snapshot(
    *,
    run_id: str,
    run_status: str,
    turn_count: int,
    elapsed_seconds: float,
    provider_status: str,
    live_read_status: str,
    artifact_count: int,
    review_queue_count: int,
    duplication_report: DrySoakDuplicationReport | None,
    resource_snapshot: DrySoakResourceSnapshot | None,
    budget_state: FailureBudgetState | None,
    dry_soak_verdict: str,
    last_heartbeat_at: str | None,
    dry_soak_base: Path | None = None,
) -> dict[str, Any]:
    freshness = assess_heartbeat_freshness(
        {"observed_at": last_heartbeat_at} if last_heartbeat_at else None
    )
    lock = read_lock(base=dry_soak_base)

    if freshness == "missing":
        truth_state = "RED_DRY_SOAK_HEARTBEAT_MISSING"
        panel_state = "RED"
    elif freshness == "stale":
        truth_state = "YELLOW_DRY_SOAK_HEARTBEAT_STALE"
        panel_state = "YELLOW"
    elif dry_soak_verdict.startswith("RED_"):
        truth_state = dry_soak_verdict
        panel_state = "RED"
    elif dry_soak_verdict.startswith("YELLOW_"):
        truth_state = dry_soak_verdict
        panel_state = "YELLOW"
    else:
        truth_state = dry_soak_verdict
        panel_state = "GREEN"

    return {
        "panel_id": "AgentZeroDrySoakMonitorPanel",
        "run_id": run_id,
        "run_status": run_status,
        "turn_count": turn_count,
        "elapsed_seconds": elapsed_seconds,
        "lock_state": lock_state(base=dry_soak_base).value,
        "stop_available": True,
        "panic_available": True,
        "last_heartbeat": last_heartbeat_at,
        "freshness_status": freshness,
        "provider_status": provider_status,
        "live_read_status": live_read_status,
        "artifact_count": artifact_count,
        "review_queue_count": review_queue_count,
        "duplicate_body_hash_rate": duplication_report.duplicate_body_hash_rate if duplication_report else 0.0,
        "duplication_verdict": duplication_report.verdict if duplication_report else "unknown",
        "resource_verdict": resource_snapshot.verdict if resource_snapshot else "unknown",
        "failure_budget_verdict": budget_state.verdict if budget_state else "unknown",
        "truth_state": truth_state,
        "generated_at": last_heartbeat_at or now_iso(),
        "expires_at": None,
        "verdict": dry_soak_verdict,
        "panel_state": panel_state,
        "source_refs": [str(run_dry_soak_dir(run_id, base=dry_soak_base))],
        "direct_external_actions_allowed": False,
        "approve_available": False,
        "publish_available": False,
        "send_available": False,
    }


from hg_runtime.dry_soak.storage import run_dry_soak_dir  # noqa: E402

__all__ = ["build_exciton_dry_soak_snapshot"]
