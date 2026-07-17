"""GitHub boot/shutdown anchor recording for Agent Zero dry autonomous loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_runtime.external_witness_journal.remote_freshness import check_remote_witness_freshness
from hg_runtime.lifecycle_anchor_autopilot.hooks import dispatch_boot_start, dispatch_clean_stop, dispatch_panic_entered
from hg_runtime.lifecycle_anchor_autopilot.push_resolver import resolve_lifecycle_push_policy

WORKSPACE = Path(__file__).resolve().parents[2]


def _push_requested() -> bool:
    return resolve_lifecycle_push_policy().push_requested


def record_loop_boot_anchor(
    *,
    run_id: str,
    agent_id: str,
    schedule_mode: str,
    max_iterations: int,
    max_duration_seconds: int,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """Record BOOT_START to local witness journal; live-push to GitHub when policy allows."""
    push = _push_requested()
    dry = dry_run if dry_run is not None else not push
    facts = {
        "component": "dry_autonomous_loop",
        "phase": "13",
        "run_id": run_id,
        "agent_id": agent_id,
        "schedule_mode": schedule_mode,
        "max_iterations": max_iterations,
        "max_duration_seconds": max_duration_seconds,
    }
    return dispatch_boot_start(
        summary=f"Agent Zero bounded dry loop boot: {run_id}",
        facts=facts,
        operator_invoked=True,
        push_requested=push,
        dry_run=dry,
        run_id=run_id,
    )


def record_loop_shutdown_anchor(
    *,
    run_id: str,
    agent_id: str,
    verdict: str,
    iteration_count: int,
    panic: bool = False,
    dry_run: bool | None = None,
) -> dict[str, Any]:
    """Record CLEAN_STOP or PANIC_ENTERED; live-push when policy allows."""
    push = _push_requested()
    dry = dry_run if dry_run is not None else not push
    facts = {
        "component": "dry_autonomous_loop",
        "phase": "13",
        "run_id": run_id,
        "agent_id": agent_id,
        "verdict": verdict,
        "iteration_count": iteration_count,
    }
    if panic:
        return dispatch_panic_entered(
            summary=f"Agent Zero dry loop panic shutdown: {run_id}",
            facts=facts,
            operator_invoked=True,
            push_requested=push,
            dry_run=dry,
            run_id=run_id,
        )
    return dispatch_clean_stop(
        summary=f"Agent Zero bounded dry loop shutdown: {run_id} ({verdict})",
        facts=facts,
        operator_invoked=True,
        push_requested=push,
        dry_run=dry,
        run_id=run_id,
    )


def verify_github_anchor_freshness() -> dict[str, Any]:
    """Check remote witness freshness after push; honest YELLOW when local-only."""
    freshness = check_remote_witness_freshness(workspace=WORKSPACE)
    payload = freshness.to_payload()
    if freshness.stale and freshness.verification_mode != "local_only":
        payload["loop_anchor_check"] = "YELLOW_REMOTE_ANCHOR_STALE"
    elif freshness.verification_mode == "local_only":
        payload["loop_anchor_check"] = "YELLOW_LOCAL_ONLY_ANCHOR_NOT_REMOTE"
    else:
        payload["loop_anchor_check"] = "GREEN_REMOTE_ANCHOR_FRESH"
    return payload


def anchor_committed(receipt: dict[str, Any] | None) -> bool:
    if not receipt:
        return False
    return bool(receipt.get("local_committed") or receipt.get("journal_receipt_id"))


__all__ = [
    "anchor_committed",
    "record_loop_boot_anchor",
    "record_loop_shutdown_anchor",
    "verify_github_anchor_freshness",
]
