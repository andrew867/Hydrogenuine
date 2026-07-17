"""Phase 39 deterministic stability loop.

Runs a dry-run task queue for many iterations, checkpointing periodically and
honoring preemption with strict precedence: PANIC preempts STOP preempts work.
The loop never applies a patch, grants authority, authorizes a tool, calls an
external provider, or creates a live effect. A task that attempts to flip a
boundary flag is rejected and the flag stays false.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.long_run_stability.boundary_monitor import (
    boundary_snapshot,
    boundary_state_hash,
    detect_boundary_drift,
)
from hg_runtime.long_run_stability.checkpoint import make_checkpoint
from hg_runtime.long_run_stability.receipt_writer import ReceiptChain
from hg_runtime.long_run_stability.replay import GENESIS_HASH
from hg_runtime.long_run_stability.schemas import (
    BOUNDARY_FLAG_FIELDS,
    EVENT_BOUNDARY_DRIFT_REJECTED,
    EVENT_CHECKPOINT_WRITTEN,
    EVENT_CRASH,
    EVENT_PANIC_PREEMPTION,
    EVENT_SOAK_COMPLETED,
    EVENT_STOP_PREEMPTION,
    EVENT_TASK_PROCESSED,
    HALT_COMPLETED,
    HALT_CRASH,
    HALT_PANIC,
    HALT_STOP,
    MODE_SHORT_FIXTURE_SOAK,
    PHASE19_STATUS,
    PHASE24_STATUS,
    STABILITY_LOOP_EVENT_SCHEMA,
    STABILITY_LOOP_STATE_SCHEMA,
    STOP_PANIC_EVENT_SCHEMA,
    assert_neutral_output,
    neutral_boundary_flags,
)

DEFAULT_CHECKPOINT_INTERVAL = 2


def soak_config(*, checkpoint_interval: int = DEFAULT_CHECKPOINT_INTERVAL, mode: str = MODE_SHORT_FIXTURE_SOAK) -> dict[str, Any]:
    return {
        "schema": "long_run_soak_config_v1",
        "checkpoint_interval": int(checkpoint_interval),
        "mode": mode,
        "fixture_only": True,
        "local_only": True,
        **neutral_boundary_flags(),
    }


def final_state_hash(state: Mapping[str, Any]) -> str:
    from hg_runtime.memory_ledger.hash_chain import canonical_hash

    desc = {
        "task_queue_hash": state["task_queue_hash"],
        "iteration": int(state["iteration"]),
        "task_cursor": int(state["task_cursor"]),
        **{field: bool(state.get(field, False)) for field in BOUNDARY_FLAG_FIELDS},
        "stop_requested": bool(state.get("stop_requested")),
        "panic_requested": bool(state.get("panic_requested")),
        "phase19_status": state.get("phase19_status", PHASE19_STATUS),
        "phase24_status": state.get("phase24_status", PHASE24_STATUS),
    }
    return canonical_hash(desc)


def _initial_state(run_id: str, mode: str, queue_hash: str) -> dict[str, Any]:
    state = {
        "schema": STABILITY_LOOP_STATE_SCHEMA,
        "run_id": run_id,
        "mode": mode,
        "iteration": 0,
        "task_cursor": 0,
        "task_queue_hash": queue_hash,
        "checkpoint_id": None,
        "checkpoint_hash": None,
        "receipt_chain_root": GENESIS_HASH,
        "event_log_head": GENESIS_HASH,
        "stop_requested": False,
        "panic_requested": False,
        "phase19_status": PHASE19_STATUS,
        "phase24_status": PHASE24_STATUS,
        "final_state_hash": None,
        **neutral_boundary_flags(),
    }
    state["boundary_state_hash"] = boundary_state_hash(state)
    return state


def run_soak(
    config: Mapping[str, Any],
    queue: Mapping[str, Any],
    *,
    run_id: str,
    mode: str = MODE_SHORT_FIXTURE_SOAK,
    stop_at: int | None = None,
    panic_at: int | None = None,
    crash_at: int | None = None,
    resume_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    tasks = queue["tasks"]
    count = len(tasks)
    interval = max(1, int(config.get("checkpoint_interval", DEFAULT_CHECKPOINT_INTERVAL)))

    state = _initial_state(run_id, mode, queue["queue_hash"])
    if resume_state is not None:
        for field in (
            "iteration",
            "task_cursor",
            "receipt_chain_root",
            "stop_requested",
            "panic_requested",
            *BOUNDARY_FLAG_FIELDS,
        ):
            if field in resume_state:
                state[field] = resume_state[field]
        # A clean resume clears any prior stop/panic so the run can complete.
        state["stop_requested"] = False
        state["panic_requested"] = False
        state["boundary_state_hash"] = boundary_state_hash(state)

    start_head = state["receipt_chain_root"]
    chain = ReceiptChain(head=state["receipt_chain_root"])
    events: list[dict[str, Any]] = []
    checkpoints: list[dict[str, Any]] = []
    stop_panic_events: list[dict[str, Any]] = []
    boundary_snapshots: list[dict[str, Any]] = []
    checkpoint_sequence = 0
    last_checkpoint_cursor = -1

    def emit(kind: str, extra: Mapping[str, Any] | None = None) -> None:
        payload = {
            "schema": STABILITY_LOOP_EVENT_SCHEMA,
            "kind": kind,
            "run_id": run_id,
            "iteration": state["iteration"],
            "task_cursor": state["task_cursor"],
            **(dict(extra) if extra else {}),
        }
        assert_neutral_output(payload)
        record = chain.append(STABILITY_LOOP_EVENT_SCHEMA, payload)
        events.append(record)
        state["receipt_chain_root"] = chain.head
        state["event_log_head"] = chain.head

    def write_checkpoint() -> None:
        nonlocal checkpoint_sequence, last_checkpoint_cursor
        record = make_checkpoint(state, sequence=checkpoint_sequence)
        assert_neutral_output(record)
        checkpoints.append(record)
        state["checkpoint_id"] = record["checkpoint_id"]
        state["checkpoint_hash"] = record["checkpoint_hash"]
        boundary_snapshots.append(boundary_snapshot(state, iteration=state["iteration"]))
        emit(EVENT_CHECKPOINT_WRITTEN, {"checkpoint_id": record["checkpoint_id"], "checkpoint_hash": record["checkpoint_hash"]})
        checkpoint_sequence += 1
        last_checkpoint_cursor = state["task_cursor"]

    halt_reason = HALT_COMPLETED
    crashed = False
    crash_iteration = -1

    while state["task_cursor"] < count:
        i = state["task_cursor"]
        # Precedence: PANIC preempts STOP preempts work.
        if panic_at is not None and i == panic_at:
            state["panic_requested"] = True
            stop_panic_events.append(
                {"schema": STOP_PANIC_EVENT_SCHEMA, "kind": "PANIC", "iteration": i, "preempts": ["STOP", "WORK"]}
            )
            emit(EVENT_PANIC_PREEMPTION, {"preempts_stop": True, "preempts_work": True})
            halt_reason = HALT_PANIC
            break
        if stop_at is not None and i == stop_at:
            state["stop_requested"] = True
            stop_panic_events.append(
                {"schema": STOP_PANIC_EVENT_SCHEMA, "kind": "STOP", "iteration": i, "preempts": ["WORK"]}
            )
            emit(EVENT_STOP_PREEMPTION, {"preempts_work": True})
            write_checkpoint()
            halt_reason = HALT_STOP
            break
        if crash_at is not None and i == crash_at:
            emit(EVENT_CRASH, {"abrupt": True})
            halt_reason = HALT_CRASH
            crashed = True
            crash_iteration = i
            break

        task = tasks[i]
        drift = detect_boundary_drift(task.get("attempted_effect") or {})
        if drift:
            # Reject the attempt; boundary flags stay false (never honored).
            emit(EVENT_BOUNDARY_DRIFT_REJECTED, {"task_id": task["task_id"], "attempted_fields": drift, "honored": False})
        else:
            emit(EVENT_TASK_PROCESSED, {"task_id": task["task_id"], "kind": task["kind"]})
        state["task_cursor"] += 1
        state["iteration"] += 1
        if state["task_cursor"] % interval == 0:
            write_checkpoint()

    if halt_reason == HALT_COMPLETED:
        if last_checkpoint_cursor != state["task_cursor"]:
            write_checkpoint()
        emit(EVENT_SOAK_COMPLETED, {"tasks_processed": state["task_cursor"]})

    state["boundary_state_hash"] = boundary_state_hash(state)
    state["final_state_hash"] = final_state_hash(state)
    assert_neutral_output(state)

    return {
        "run_id": run_id,
        "mode": mode,
        "halt_reason": halt_reason,
        "crashed": crashed,
        "crash_iteration": crash_iteration,
        "queue_hash": queue["queue_hash"],
        "receipt_chain_start": start_head,
        "task_count": count,
        "tasks_processed": state["task_cursor"],
        "state": state,
        "final_state_hash": state["final_state_hash"],
        "receipt_chain_root": state["receipt_chain_root"],
        "events": events,
        "checkpoints": checkpoints,
        "stop_panic_events": stop_panic_events,
        "boundary_snapshots": boundary_snapshots,
    }


__all__ = ["soak_config", "run_soak", "final_state_hash", "DEFAULT_CHECKPOINT_INTERVAL"]
