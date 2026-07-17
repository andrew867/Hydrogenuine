"""Phase 39 long-run stability, recovery, and checkpoint soak.

Orchestrates a deterministic, fixture-only soak over Phase 37/38
review-preparation tasks and proves the substrate can run for many iterations,
checkpoint, be preempted by STOP/PANIC, recover from a crash via its last valid
checkpoint, and replay to an identical final state.

Strictly soak/recovery infrastructure: no patch is applied, no authority is
granted, no tool is authorized, no live effect or live post is created, no
external provider is called, and STOP/PANIC is never weakened.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.long_run_stability.boundary_monitor import boundary_snapshot
from hg_runtime.long_run_stability.checkpoint import build_manifest, verify_manifest, verify_checkpoint
from hg_runtime.long_run_stability.invariant_monitor import check_run_invariants, invariant_snapshot
from hg_runtime.long_run_stability.loop import final_state_hash, run_soak, soak_config
from hg_runtime.long_run_stability.recovery import recover_and_resume, reject_corrupted_checkpoint
from hg_runtime.long_run_stability.replay import GENESIS_HASH, replay_records
from hg_runtime.long_run_stability.schemas import (
    BOUNDARY_FLAG_FIELDS,
    HALT_PANIC,
    HALT_STOP,
    MODE_CRASH_RECOVERY,
    MODE_PANIC_PREEMPTION,
    MODE_STOP_PREEMPTION,
)
from hg_runtime.long_run_stability.task_queue import build_task_queue


def compute_replay(run: Mapping[str, Any]) -> dict[str, Any]:
    """Replay a run's recorded events/state and verify it reproduces itself."""
    start_head = run.get("receipt_chain_start") or GENESIS_HASH
    rec = replay_records(run["events"], start_head=start_head)
    root_matches = bool(rec["ok"]) and rec["chain_root"] == run["receipt_chain_root"]
    final_matches = final_state_hash(run["state"]) == run["final_state_hash"]

    rejects_mutation = True
    events = run["events"]
    if events:
        mutated = [dict(r) for r in events]
        tail = dict(mutated[-1])
        payload = dict(tail["payload"])
        payload["kind"] = "TAMPERED"
        tail["payload"] = payload
        mutated[-1] = tail
        rejects_mutation = not replay_records(mutated, start_head=start_head)["ok"]

    return {
        "ok": root_matches and final_matches,
        "receipt_chain_root_matches": root_matches,
        "final_state_hash_matches": final_matches,
        "rejects_mutation": rejects_mutation,
        "replay": rec,
    }


def evaluate_scenario(fixture: Mapping[str, Any], *, config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run one soak scenario fixture and return its full evidence bundle."""
    config = config or soak_config()
    queue = build_task_queue(fixture["tasks"])
    name = fixture["name"]
    run_id = f"p39-{name.lower()}"
    mode = fixture["mode"]

    # An uninterrupted baseline run over the same queue (resume must match it).
    baseline = run_soak(config, queue, run_id=f"{run_id}-baseline")

    bundle: dict[str, Any] = {
        "name": name,
        "mode": mode,
        "queue_hash": queue["queue_hash"],
        "task_count": queue["count"],
        "baseline_final_state_hash": baseline["final_state_hash"],
        "checkpoint_count": len(baseline["checkpoints"]),
        # Coverage flags (default false; set per branch below).
        "stop_preempts_work": False,
        "panic_preempts_stop_and_work": False,
        "crash_recovery_demonstrated": False,
        "corrupted_checkpoint_rejected": False,
        "boundary_drift_rejected": False,
        "resume_matches_uninterrupted_run": False,
    }

    if mode == MODE_STOP_PREEMPTION:
        run = run_soak(config, queue, run_id=run_id, mode=mode, stop_at=fixture["stop_at"])
        bundle["stop_preempts_work"] = run["halt_reason"] == HALT_STOP and run["tasks_processed"] < queue["count"]
    elif mode == MODE_PANIC_PREEMPTION:
        run = run_soak(config, queue, run_id=run_id, mode=mode, panic_at=fixture["panic_at"])
        bundle["panic_preempts_stop_and_work"] = (
            run["halt_reason"] == HALT_PANIC
            and not run["state"]["stop_requested"]
            and run["tasks_processed"] < queue["count"]
        )
    elif mode == MODE_CRASH_RECOVERY:
        run = run_soak(config, queue, run_id=run_id, mode=mode, crash_at=fixture["crash_at"])
        checkpoints = run["checkpoints"]
        if fixture.get("corrupt_checkpoint") and checkpoints:
            corrupted = dict(checkpoints[-1])
            corrupted["checkpoint_hash"] = "sha256:deadbeefcorruptedcheckpointvalue00000000000000000000000000000000"
            rejection = reject_corrupted_checkpoint(corrupted)
            bundle["corrupted_checkpoint_rejected"] = not rejection["ok"] and not verify_checkpoint(corrupted)
            bundle["recovery_result"] = rejection
        else:
            recovery = recover_and_resume(config, queue, checkpoints, run_id=f"{run_id}-resume")
            run = recovery["run"] or run
            bundle["crash_recovery_demonstrated"] = bool(recovery["ok"])
            bundle["resume_matches_uninterrupted_run"] = (
                recovery["ok"] and recovery["final_state_hash"] == baseline["final_state_hash"]
            )
            bundle["recovery_result"] = {k: v for k, v in recovery.items() if k != "run"}
    else:  # SHORT_FIXTURE_SOAK (stable, boundary-drift, fake-green)
        run = baseline
        drift_events = [e for e in run["events"] if e["payload"]["kind"] == "BOUNDARY_DRIFT_REJECTED"]
        if any(t.get("attempted_effect") for t in queue["tasks"]):
            bundle["boundary_drift_rejected"] = bool(drift_events) and not any(
                run["state"].get(field) for field in BOUNDARY_FLAG_FIELDS
            )

    bundle["run"] = run
    bundle["halt_reason"] = run["halt_reason"]
    bundle["tasks_processed"] = run["tasks_processed"]
    bundle["final_state_hash"] = run["final_state_hash"]
    bundle["receipt_chain_root"] = run["receipt_chain_root"]
    bundle["checkpoint_manifest"] = build_manifest(run["checkpoints"])
    bundle["checkpoint_manifest_valid"] = verify_manifest(run["checkpoints"], bundle["checkpoint_manifest"])
    bundle["invariant_snapshot"] = invariant_snapshot(run)
    bundle["invariant_failures"] = check_run_invariants(run)
    bundle["boundary_snapshot"] = boundary_snapshot(run["state"], iteration=run["state"]["iteration"])
    bundle["replay_eval"] = compute_replay(run)
    bundle["boundary_flags_false"] = not any(run["state"].get(field) for field in BOUNDARY_FLAG_FIELDS)
    bundle["fake_green"] = bool(fixture.get("fake_green"))
    return bundle


__all__ = [
    "evaluate_scenario",
    "compute_replay",
    "run_soak",
    "soak_config",
    "build_task_queue",
    "recover_and_resume",
    "final_state_hash",
]
