"""Loop heartbeat records."""

from __future__ import annotations

import uuid
from pathlib import Path

from hg_runtime.agent_zero_state.hashing import hash_record
from hg_runtime.dry_autonomous_loop.loop_lock import lock_state
from hg_runtime.dry_autonomous_loop.schema import now_iso


def build_heartbeat(
    *,
    run_id: str,
    iteration_index: int,
    elapsed_seconds: float,
    provider_status: str,
    live_read_status: str,
    artifact_count: int,
    review_queue_count: int,
    last_turn_ref: str | None,
    last_turn_verdict: str | None,
    failure_budget_status: str,
    resource_status: str,
    duplication_status: str,
    verdict: str,
    loop_base: Path | None = None,
) -> dict:
    body = {
        "heartbeat_id": f"hb-{uuid.uuid4().hex[:12]}",
        "run_id": run_id,
        "iteration_index": iteration_index,
        "observed_at": now_iso(),
        "elapsed_seconds": elapsed_seconds,
        "lock_state": lock_state(base=loop_base).value,
        "stop_available": True,
        "panic_available": True,
        "last_turn_ref": last_turn_ref,
        "last_turn_verdict": last_turn_verdict,
        "provider_status": provider_status,
        "live_read_status": live_read_status,
        "artifact_count": artifact_count,
        "review_queue_count": review_queue_count,
        "failure_budget_status": failure_budget_status,
        "resource_status": resource_status,
        "duplication_status": duplication_status,
        "verdict": verdict,
    }
    body["hash"] = hash_record({k: v for k, v in body.items() if k != "hash"})
    return body


__all__ = ["build_heartbeat"]
