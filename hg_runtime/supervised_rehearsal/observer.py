"""Rehearsal observer heartbeats."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record
from hg_runtime.supervised_rehearsal.rehearsal_store import RehearsalStore
from hg_runtime.supervised_rehearsal.run_lock import lock_state, read_lock
from hg_runtime.supervised_rehearsal.schema import now_iso
from hg_runtime.supervised_rehearsal.stop_panic import stop_panic_status


HEARTBEAT_STALE_SECONDS = 120


def build_observer_heartbeat(
    *,
    run_id: str,
    heartbeat_index: int,
    turn_count: int,
    current_stage: str,
    last_turn_ref: str | None = None,
    provider_status: str = "unavailable",
    live_read_status: str = "unavailable",
    review_queue_status: str = "unknown",
    verdict: str = "GREEN_OBSERVER_HEARTBEAT",
    base: Path | None = None,
    stop_path: str | None = None,
    panic_path: str | None = None,
) -> dict[str, Any]:
    sp = stop_panic_status(run_id, base=base, stop_path=stop_path, panic_path=panic_path)
    payload = {
        "run_id": run_id,
        "heartbeat_index": heartbeat_index,
        "observed_at": now_iso(),
        "turn_count": turn_count,
        "current_stage": current_stage,
        "last_turn_ref": last_turn_ref,
        "lock_state": lock_state(base=base).value,
        "stop_available": sp.get("stop_available", True),
        "panic_available": sp.get("panic_available", True),
        "provider_status": provider_status,
        "live_read_status": live_read_status,
        "review_queue_status": review_queue_status,
        "verdict": verdict,
    }
    payload["hash"] = hash_record(payload)
    return payload


def write_observer_heartbeat(store: RehearsalStore, heartbeat: dict[str, Any]) -> Path:
    return store.store_observer_heartbeat(heartbeat)


def assess_heartbeat_freshness(heartbeat: dict[str, Any] | None) -> str:
    if not heartbeat:
        return "missing"
    observed = heartbeat.get("observed_at", "")
    try:
        from datetime import datetime, timezone

        ts = datetime.fromisoformat(observed.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > HEARTBEAT_STALE_SECONDS:
            return "stale"
        return "fresh"
    except Exception:
        return "stale"


__all__ = [
    "HEARTBEAT_STALE_SECONDS",
    "assess_heartbeat_freshness",
    "build_observer_heartbeat",
    "write_observer_heartbeat",
]
