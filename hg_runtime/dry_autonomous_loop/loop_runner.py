"""Bounded dry autonomous loop runner — in-process only."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.agent_turn_engine.engine import run_single_agent_turn
from hg_runtime.agent_turn_engine.schema import AgentTurnFailure, AgentTurnResult, AgentTurnVerdict, build_agent_turn_request
from hg_runtime.agent_turn_engine.turn_storage import turns_root
from hg_runtime.dry_autonomous_loop.anchor_lifecycle import (
    anchor_committed,
    record_loop_boot_anchor,
    record_loop_shutdown_anchor,
    verify_github_anchor_freshness,
)
from hg_runtime.dry_autonomous_loop.errors import DryAutonomousLoopLockError, DryAutonomousLoopRunnerError
from hg_runtime.dry_autonomous_loop.heartbeat import build_heartbeat
from hg_runtime.dry_autonomous_loop.loop_lock import acquire_lock, heartbeat_lock, release_lock
from hg_runtime.dry_autonomous_loop.postflight import run_loop_postflight
from hg_runtime.dry_autonomous_loop.readiness import build_readiness_report, persist_readiness, write_readiness_md
from hg_runtime.dry_autonomous_loop.run_state import LoopRunStore
from hg_runtime.dry_autonomous_loop.scheduler import (
    SchedulerState,
    compute_sleep_seconds,
    new_scheduler_state,
    should_continue,
    sleep_bounded,
)
from hg_runtime.dry_autonomous_loop.schema import (
    DryAutonomousLoopConfig,
    DryAutonomousLoopIteration,
    DryAutonomousLoopRun,
    DryAutonomousLoopState,
    DryAutonomousLoopVerdict,
    now_iso,
    validate_loop_config,
)
from hg_runtime.dry_autonomous_loop.stop_panic import check_panic, check_stop, ensure_stop_panic_available
from hg_runtime.dry_autonomous_loop.storage import current_lock_path, loop_root, write_json
from hg_runtime.dry_soak.duplication_watchdog import analyze_duplication
from hg_runtime.dry_soak.errors import FailureBudgetExceeded
from hg_runtime.dry_soak.failure_budget import new_failure_budget_state
from hg_runtime.dry_soak.resource_watchdog import adjusted_turn_interval, collect_resource_snapshot


def _elapsed_seconds(started_at: str) -> float:
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - start).total_seconds()
    except Exception:
        return 0.0


def _turn_base(*, turn_base: Path | None = None) -> Path:
    if turn_base:
        return turn_base
    env = os.environ.get("HG_AGENT_TURN_BASE")
    if env:
        return Path(env)
    return turns_root()


def run_bounded_dry_autonomous_loop(
    config: DryAutonomousLoopConfig,
    *,
    loop_base: Path | None = None,
    turn_base: Path | None = None,
    provider_invoke=None,
) -> DryAutonomousLoopRun:
    config = validate_loop_config(config)
    base = loop_base or loop_root()
    store = LoopRunStore(config.run_id, base=base)
    run_dir = store.root
    run_dir.mkdir(parents=True, exist_ok=True)

    if not config.stop_file_path:
        config = DryAutonomousLoopConfig(**{**config.__dict__, "stop_file_path": str(run_dir / "STOP")})
    if not config.panic_file_path:
        config = DryAutonomousLoopConfig(**{**config.__dict__, "panic_file_path": str(run_dir / "PANIC")})

    store.write_config(config.to_payload())

    try:
        acquire_lock(config.run_id, base=base)
    except DryAutonomousLoopLockError as exc:
        raise DryAutonomousLoopRunnerError(f"RED_DRY_AUTONOMOUS_LOOP_LOCK_FAILURE:{exc}") from exc

    ensure_stop_panic_available(
        config.run_id,
        base=base,
        stop_path=config.stop_file_path,
        panic_path=config.panic_file_path,
    )

    if check_panic(config.run_id, base=base, panic_path=config.panic_file_path):
        release_lock(config.run_id, status="panic", base=base)
        raise DryAutonomousLoopRunnerError("RED_DRY_AUTONOMOUS_LOOP_STOP_PANIC_FAILURE")

    boot_anchor = record_loop_boot_anchor(
        run_id=config.run_id,
        agent_id=config.agent_id,
        schedule_mode=config.schedule_mode,
        max_iterations=config.max_iterations,
        max_duration_seconds=config.max_duration_seconds,
    )
    boot_ref = boot_anchor.get("journal_receipt_id") or boot_anchor.get("receipt_id")

    tbase = _turn_base(turn_base=turn_base)
    budget = new_failure_budget_state()
    sched = new_scheduler_state()
    started_at = now_iso()
    iterations: list[DryAutonomousLoopIteration] = []
    heartbeat_refs: list[str] = []
    turn_refs: list[str] = []
    stop_events = 0
    panic_events = 0
    deferred_turns = 0
    final_status = DryAutonomousLoopState.COMPLETED
    final_verdict = DryAutonomousLoopVerdict.GREEN_DRY_AUTONOMOUS_LOOP_COMPLETE
    provider_status = "available" if config.allow_provider else "unavailable"
    live_read_status = "available" if config.allow_live_read else "unavailable"
    last_artifact_count = 0
    last_review_count = 0
    resource_throttled = False
    lock_released = False

    def _stop() -> bool:
        return check_stop(config.run_id, base=base, stop_path=config.stop_file_path)

    def _panic() -> bool:
        return check_panic(config.run_id, base=base, panic_path=config.panic_file_path)

    while should_continue(sched, config):
        if _panic():
            panic_events += 1
            final_status = DryAutonomousLoopState.PANIC
            final_verdict = DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_STOPPED_BY_OPERATOR
            break

        if sched.iteration > 0 and _stop():
            stop_events += 1
            final_status = DryAutonomousLoopState.STOPPED
            final_verdict = DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_STOPPED_BY_OPERATOR
            break

        sched.iteration += 1
        heartbeat_lock(config.run_id, base=base)
        turn_start = time.monotonic()

        request = build_agent_turn_request(
            agent_id=config.agent_id,
            run_id=config.run_id,
            runtime_mode=config.runtime_mode,
            operator_presence="operator_present" if config.operator_present else "operator_absent",
            allow_live_read=config.allow_live_read,
            allow_provider=config.allow_provider,
        )
        outcome = run_single_agent_turn(
            request,
            provider_invoke=provider_invoke if config.allow_provider else None,
            base=tbase,
        )

        if isinstance(outcome, AgentTurnFailure) or (
            isinstance(outcome, AgentTurnResult) and outcome.verdict.value.startswith("RED_")
        ):
            release_lock(config.run_id, status="failed", base=base)
            lock_released = True
            raise DryAutonomousLoopRunnerError(f"RED_DRY_AUTONOMOUS_LOOP_RECEIPT_GAP:{outcome.verdict.value}")

        if not outcome.turn_receipt_ref:
            release_lock(config.run_id, status="failed", base=base)
            lock_released = True
            raise DryAutonomousLoopRunnerError("RED_DRY_AUTONOMOUS_LOOP_RECEIPT_GAP")

        if outcome.verdict in (
            AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_PROVIDER_UNAVAILABLE,
            AgentTurnVerdict.YELLOW_AGENT_TURN_RESTED,
            AgentTurnVerdict.YELLOW_AGENT_TURN_WITNESS_ONLY,
        ):
            deferred_turns += 1
            budget.record_provider_unavailable()
        else:
            budget.record_provider_available()

        if outcome.verdict == AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_LIVE_READ_UNAVAILABLE:
            budget.record_live_read_unavailable()

        resource_snap = collect_resource_snapshot(
            run_id=config.run_id,
            turn_index=outcome.turn_index,
            turn_duration_seconds=time.monotonic() - turn_start,
            turn_base=tbase,
            dry_soak_root=base,
        )
        last_artifact_count = resource_snap.artifact_count
        last_review_count = resource_snap.review_queue_count
        budget.record_queue_growth(resource_snap.review_queue_count)
        resource_throttled = resource_snap.verdict == "YELLOW_DRY_SOAK_RESOURCE_PRESSURE"
        if resource_throttled:
            final_verdict = DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_RESOURCE_THROTTLED

        dup_report = analyze_duplication(
            run_id=config.run_id,
            turn_index=outcome.turn_index,
            turn_verdict=outcome.verdict.value,
            turn_base=tbase,
        )
        try:
            budget.record_duplicate_rate(dup_report.duplicate_body_hash_rate)
            if dup_report.verdict.startswith("RED_"):
                if "FIXTURE" in dup_report.verdict:
                    budget.record_fixture_truth()
                else:
                    budget.record_duplicate_rate(1.0)
        except FailureBudgetExceeded as exc:
            final_status = DryAutonomousLoopState.FAILED
            final_verdict = DryAutonomousLoopVerdict(exc.verdict)
            break

        iteration = DryAutonomousLoopIteration(
            iteration_index=sched.iteration,
            turn_receipt_ref=outcome.turn_receipt_ref,
            turn_verdict=outcome.verdict.value,
            artifact_count=last_artifact_count,
            review_queue_count=last_review_count,
            created_at=outcome.created_at,
        )
        iterations.append(iteration)
        store.append_iteration(iteration.to_payload())
        turn_refs.append(outcome.turn_receipt_ref)

        hb = build_heartbeat(
            run_id=config.run_id,
            iteration_index=sched.iteration,
            elapsed_seconds=sched.elapsed_seconds(),
            provider_status=provider_status,
            live_read_status=live_read_status,
            artifact_count=last_artifact_count,
            review_queue_count=last_review_count,
            last_turn_ref=outcome.turn_receipt_ref,
            last_turn_verdict=outcome.verdict.value,
            failure_budget_status=budget.verdict,
            resource_status=resource_snap.verdict,
            duplication_status=dup_report.verdict,
            verdict=final_verdict.value,
            loop_base=base,
        )
        store.append_heartbeat(hb)
        heartbeat_refs.append(hb["heartbeat_id"])
        write_json(run_dir / "exciton_snapshot.json", hb)

        store.write_state_snapshot(
            status=final_status if final_status != DryAutonomousLoopState.COMPLETED else DryAutonomousLoopState.RUNNING,
            iteration_count=len(iterations),
            last_turn_ref=outcome.turn_receipt_ref,
            verdict=final_verdict.value,
        )

        if _panic():
            panic_events += 1
            final_status = DryAutonomousLoopState.PANIC
            final_verdict = DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_STOPPED_BY_OPERATOR
            break
        if _stop():
            stop_events += 1
            final_status = DryAutonomousLoopState.STOPPED
            final_verdict = DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_STOPPED_BY_OPERATOR
            break

        if sched.iteration < config.max_iterations and should_continue(sched, config):
            sleep_secs = compute_sleep_seconds(config, resource_throttled=resource_throttled)
            if config.schedule_mode == "fixed_interval":
                sleep_secs = adjusted_turn_interval(sleep_secs, resource_snap)
            if sleep_bounded(sleep_secs, config, check_stop=_stop, check_panic=_panic):
                if _panic():
                    panic_events += 1
                    final_status = DryAutonomousLoopState.PANIC
                    final_verdict = DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_STOPPED_BY_OPERATOR
                else:
                    stop_events += 1
                    final_status = DryAutonomousLoopState.STOPPED
                    final_verdict = DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_STOPPED_BY_OPERATOR
                break

    if deferred_turns and final_verdict == DryAutonomousLoopVerdict.GREEN_DRY_AUTONOMOUS_LOOP_COMPLETE:
        if not config.allow_provider:
            final_verdict = DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_PROVIDER_UNAVAILABLE
        elif deferred_turns == len(iterations):
            final_verdict = DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_COMPLETED_WITH_DEFERRED_TURNS

    if not config.allow_live_read and deferred_turns:
        if final_verdict == DryAutonomousLoopVerdict.GREEN_DRY_AUTONOMOUS_LOOP_COMPLETE:
            final_verdict = DryAutonomousLoopVerdict.YELLOW_DRY_AUTONOMOUS_LOOP_LIVE_READ_UNAVAILABLE

    finished_at = now_iso()
    if not lock_released:
        release_lock(config.run_id, status=final_status.value, base=base)

    shutdown_anchor = record_loop_shutdown_anchor(
        run_id=config.run_id,
        agent_id=config.agent_id,
        verdict=final_verdict.value,
        iteration_count=len(iterations),
        panic=panic_events > 0,
    )
    shutdown_ref = shutdown_anchor.get("journal_receipt_id") or shutdown_anchor.get("receipt_id")
    anchor_freshness = verify_github_anchor_freshness()
    write_json(run_dir / "anchor_freshness.json", anchor_freshness)

    postflight = run_loop_postflight(
        run_id=config.run_id,
        agent_id=config.agent_id,
        started_at=started_at,
        iteration_count=len(iterations),
        stop_events=stop_events,
        panic_events=panic_events,
        loop_base=base,
        turn_base=tbase,
        boot_anchor=boot_anchor,
        shutdown_anchor=shutdown_anchor,
    )

    run = DryAutonomousLoopRun(
        run_id=config.run_id,
        agent_id=config.agent_id,
        started_at=started_at,
        finished_at=finished_at,
        status=final_status,
        config_hash=config.hash,
        lock_ref=str(current_lock_path(base=base)),
        iteration_count=len(iterations),
        iteration_refs=[f"iter-{i.iteration_index}" for i in iterations],
        turn_result_refs=turn_refs,
        heartbeat_refs=heartbeat_refs,
        stop_panic_events=[
            *([{"kind": "stop", "at": finished_at}] if stop_events else []),
            *([{"kind": "panic", "at": finished_at}] if panic_events else []),
        ],
        postflight_ref=str(run_dir / "postflight.json"),
        verdict=final_verdict,
        boot_anchor_ref=boot_ref,
        shutdown_anchor_ref=shutdown_ref,
    ).with_hash()

    readiness = build_readiness_report(
        run=run,
        duration_seconds=_elapsed_seconds(started_at),
        provider_status=provider_status,
        live_read_status=live_read_status,
        external_side_effects=postflight.external_side_effects,
        max_duration_seconds=config.max_duration_seconds,
    )
    run.readiness_verdict = readiness.readiness_verdict.value
    run = run.with_hash()

    store.write_run(run.to_payload())
    persist_readiness(readiness, run_id=config.run_id, base=base)
    write_readiness_md(readiness, run=run)

    return run


__all__ = ["run_bounded_dry_autonomous_loop"]
