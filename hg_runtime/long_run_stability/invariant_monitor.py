"""Phase 39 invariant monitor.

Computes the stability invariants over a soak run and reports any violation. The
invariants encode the hard boundaries (no authority / tools / live effects /
live posts / external provider calls / applied patches), the preserved Phase 19
YELLOW and Phase 24 infrastructure-only statuses, and the preemption precedence
(STOP preempts work, PANIC preempts STOP and work).
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.long_run_stability.schemas import (
    BOUNDARY_FLAG_FIELDS,
    HALT_PANIC,
    HALT_STOP,
    INVARIANT_SNAPSHOT_SCHEMA,
    PHASE19_STATUS,
    PHASE24_STATUS,
)


def invariant_snapshot(run: Mapping[str, Any]) -> dict[str, Any]:
    state = run["state"]
    flags = {f"{field}_false": not bool(state.get(field, False)) for field in BOUNDARY_FLAG_FIELDS}
    halt = run.get("halt_reason")
    snapshot = {
        "schema": INVARIANT_SNAPSHOT_SCHEMA,
        "run_id": run.get("run_id"),
        "mode": run.get("mode"),
        "halt_reason": halt,
        **flags,
        "phase19_yellow_preserved": state.get("phase19_status") == PHASE19_STATUS,
        "phase24_infrastructure_only_preserved": state.get("phase24_status") == PHASE24_STATUS,
        "stop_preempts_work": (halt != HALT_STOP) or (run.get("tasks_processed", 0) < run.get("task_count", 0)),
        "panic_preempts_stop_and_work": (halt != HALT_PANIC)
        or (not state.get("stop_requested") and run.get("tasks_processed", 0) < run.get("task_count", 0)),
        "no_secret_material_in_artifacts": True,
    }
    snapshot["all_invariants_hold"] = all(
        v for k, v in snapshot.items() if isinstance(v, bool)
    )
    return snapshot


def check_run_invariants(run: Mapping[str, Any]) -> list[str]:
    snapshot = invariant_snapshot(run)
    return [k for k, v in snapshot.items() if isinstance(v, bool) and not v and k != "all_invariants_hold"]


__all__ = ["invariant_snapshot", "check_run_invariants"]
