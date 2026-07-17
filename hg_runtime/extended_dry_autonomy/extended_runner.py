"""Extended dry autonomy runner — bounded in-process endurance loop."""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.agent_turn_engine.engine import run_single_agent_turn
from hg_runtime.agent_turn_engine.schema import AgentTurnFailure, AgentTurnResult, AgentTurnVerdict, build_agent_turn_request
from hg_runtime.agent_turn_engine.turn_storage import turns_root
from hg_runtime.agent_zero_state.hashing import hash_record
from hg_runtime.dry_autonomous_loop.anchor_lifecycle import record_loop_boot_anchor, record_loop_shutdown_anchor
from hg_runtime.extended_dry_autonomy.extended_heartbeat import build_extended_heartbeat
from hg_runtime.dry_autonomous_loop.schema import DryAutonomousLoopConfig
from hg_runtime.dry_autonomous_loop.stop_panic import check_panic, check_stop
from hg_runtime.dry_autonomous_loop.scheduler import (
    SchedulerState,
    compute_sleep_seconds,
    new_scheduler_state,
    should_continue,
    sleep_bounded,
)
from hg_runtime.dry_soak.duplication_watchdog import analyze_duplication
from hg_runtime.dry_soak.resource_watchdog import adjusted_turn_interval, collect_resource_snapshot
from hg_runtime.extended_dry_autonomy.anchor_audit import audit_lifecycle_anchors
from hg_runtime.extended_dry_autonomy.checkpoint import load_checkpoint, resume_from_checkpoint, write_checkpoint
from hg_runtime.extended_dry_autonomy.endurance_budget import EnduranceBudgetExceeded, new_endurance_budget_state
from hg_runtime.extended_dry_autonomy.endurance_report import build_endurance_report, persist_endurance_report
from hg_runtime.extended_dry_autonomy.errors import ExtendedDryAutonomyLockError, ExtendedDryAutonomyRunnerError
from hg_runtime.extended_dry_autonomy.exciton_snapshot import write_exciton_snapshot
from hg_runtime.extended_dry_autonomy.extended_lock import acquire_lock, heartbeat_lock, release_lock
from hg_runtime.extended_dry_autonomy.pause_resume import (
    pause_requested,
    record_pause_event,
    record_resume_event,
    resume_requested,
    wait_for_resume_or_stop,
)
from hg_runtime.extended_dry_autonomy.postflight import run_extended_postflight
from hg_runtime.extended_dry_autonomy.run_store import ExtendedRunStore
from hg_runtime.extended_dry_autonomy.schema import (
    ExtendedDryAutonomyConfig,
    ExtendedDryAutonomyRun,
    ExtendedDryAutonomyState,
    ExtendedDryAutonomyVerdict,
    ReadinessVerdict,
    now_iso,
    validate_config,
)
from hg_runtime.extended_dry_autonomy.storage import current_lock_path, write_json


def _scheduler_config(config: ExtendedDryAutonomyConfig) -> DryAutonomousLoopConfig:
    return DryAutonomousLoopConfig(
        run_id=config.run_id,
        agent_id=config.agent_id,
        schedule_mode="fixed_interval",
        max_iterations=config.max_iterations,
        max_duration_seconds=config.max_duration_seconds,
        turn_interval_seconds=config.turn_interval_seconds,
        jitter_seconds=0.0,
        created_at=config.created_at,
        hash=config.hash,
    )


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


def _should_checkpoint(
    iteration: int,
    elapsed: float,
    config: ExtendedDryAutonomyConfig,
    last_checkpoint_iter: int,
    last_checkpoint_at: float,
) -> bool:
    if iteration > 0 and iteration % max(1, config.checkpoint_every_iterations) == 0 and iteration != last_checkpoint_iter:
        return True
    if config.checkpoint_every_seconds > 0 and elapsed - last_checkpoint_at >= config.checkpoint_every_seconds:
        return True
    return False


def run_extended_dry_autonomy(
    config: ExtendedDryAutonomyConfig,
    *,
    extended_base: Path | None = None,
    turn_base: Path | None = None,
    provider_invoke=None,
) -> ExtendedDryAutonomyRun:
    config = validate_config(config)
    store = ExtendedRunStore(config.run_id, base=extended_base)
    run_dir = store.root
    run_dir.mkdir(parents=True, exist_ok=True)

    if not config.stop_file_path:
        config = ExtendedDryAutonomyConfig(**{**config.__dict__, "stop_file_path": str(run_dir / "STOP")})
    if not config.panic_file_path:
        config = ExtendedDryAutonomyConfig(**{**config.__dict__, "panic_file_path": str(run_dir / "PANIC")})
    if not config.pause_file_path:
        config = ExtendedDryAutonomyConfig(**{**config.__dict__, "pause_file_path": str(run_dir / "PAUSE")})
    if not config.resume_file_path:
        config = ExtendedDryAutonomyConfig(**{**config.__dict__, "resume_file_path": str(run_dir / "RESUME")})

    store.write_config(config.to_payload())

    try:
        acquire_lock(config.run_id, base=extended_base)
    except ExtendedDryAutonomyLockError as exc:
        raise ExtendedDryAutonomyRunnerError(f"RED_EXTENDED_DRY_AUTONOMY_LOCK_FAILURE:{exc}") from exc

    run_dir.mkdir(parents=True, exist_ok=True)
    Path(config.stop_file_path).parent.mkdir(parents=True, exist_ok=True)
    Path(config.panic_file_path).parent.mkdir(parents=True, exist_ok=True)

    if check_panic(config.run_id, panic_path=config.panic_file_path):
        release_lock(config.run_id, status="panic", base=extended_base)
        raise ExtendedDryAutonomyRunnerError("RED_EXTENDED_DRY_AUTONOMY_STOP_PANIC_FAILURE")

    boot_anchor = record_loop_boot_anchor(
        run_id=config.run_id,
        agent_id=config.agent_id,
        schedule_mode="extended_dry_autonomy",
        max_iterations=config.max_iterations,
        max_duration_seconds=config.max_duration_seconds,
    )
    boot_ref = boot_anchor.get("journal_receipt_id") or boot_anchor.get("receipt_id")

    tbase = _turn_base(turn_base=turn_base)
    budget = new_endurance_budget_state()
    sched = new_scheduler_state()
    started_at = now_iso()
    turn_refs: list[str] = []
    heartbeat_refs: list[str] = []
    checkpoint_refs: list[str] = []
    pause_resume_events: list[dict] = []
    stop_events = 0
    panic_events = 0
    pause_events = 0
    resumed_once = False
    final_status = ExtendedDryAutonomyState.COMPLETED
    final_verdict = ExtendedDryAutonomyVerdict.GREEN_EXTENDED_DRY_AUTONOMY_COMPLETE
    provider_status = "available" if config.allow_provider else "unavailable"
    live_read_status = "unavailable" if not config.allow_live_read else "degraded"
    live_read_receipt_ref: str | None = None
    provider_health_receipt_ref: str | None = None
    provider_kind: str | None = None
    model_id: str | None = None
    if config.allow_provider:
        from hg_runtime.live_provider.provider_health import probe_provider_health
        from hg_runtime.live_provider.provider_identity import build_model_identity, build_provider_identity

        health = probe_provider_health()
        provider_health_receipt_ref = health.health_receipt_id
        provider_kind = build_provider_identity().provider_kind.value
        model_id = build_model_identity(build_provider_identity()).model_id
        provider_status = "available" if health.available else "unavailable"
    if config.allow_live_read:
        from hg_runtime.live_read_endurance.read_endurance_runner import probe_live_read_status

        live_probe = probe_live_read_status()
        live_read_status = live_probe.get("status", live_read_status)
        live_read_receipt_ref = live_probe.get("receipt_ref")
    last_artifact_count = 0
    last_review_count = 0
    resource_throttled = False
    lock_released = False
    last_checkpoint_iter = 0
    last_checkpoint_mono = time.monotonic()
    shutdown_anchor: dict | None = None

    sched_cfg = _scheduler_config(config)

    def _stop() -> bool:
        return check_stop(config.run_id, stop_path=config.stop_file_path)

    def _panic() -> bool:
        return check_panic(config.run_id, panic_path=config.panic_file_path)

    initial_hb = build_extended_heartbeat(
        run_id=config.run_id,
        iteration_index=0,
        elapsed_seconds=0.0,
        provider_status=provider_status,
        live_read_status=live_read_status,
        live_read_receipt_ref=live_read_receipt_ref,
        provider_health_receipt_ref=provider_health_receipt_ref,
        provider_kind=provider_kind,
        model_id=model_id,
        artifact_count=0,
        review_queue_count=0,
        last_turn_ref=None,
        last_turn_verdict="initialized",
        endurance_budget_status=budget.verdict,
        resource_status="GREEN",
        duplication_status="GREEN",
        verdict=final_verdict.value,
        extended_base=extended_base,
    )
    store.append_heartbeat(initial_hb)
    heartbeat_refs.append(initial_hb["heartbeat_id"])

    while should_continue(sched, sched_cfg):
        if _panic():
            panic_events += 1
            final_status = ExtendedDryAutonomyState.PANIC
            final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_STOPPED_BY_OPERATOR
            break

        if sched.iteration > 0 and _stop():
            stop_events += 1
            final_status = ExtendedDryAutonomyState.STOPPED
            final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_STOPPED_BY_OPERATOR
            break

        if pause_requested(config.run_id, base=extended_base, pause_path=config.pause_file_path):
            cp = write_checkpoint(
                run_id=config.run_id,
                iteration_index=sched.iteration,
                turn_result_ref=turn_refs[-1] if turn_refs else None,
                heartbeat_hash=hash_record(initial_hb),
                boot_anchor_ref=boot_ref,
                extended_base=extended_base,
                turn_base=tbase,
            )
            checkpoint_refs.append(cp.checkpoint_id)
            pause_state = record_pause_event(
                config.run_id, checkpoint_id=cp.checkpoint_id, base=extended_base, pause_path=config.pause_file_path
            )
            pause_events += 1
            pause_resume_events.extend(pause_state.events)
            store.write_state_snapshot(
                status=ExtendedDryAutonomyState.PAUSED,
                iteration_count=sched.iteration,
                last_turn_ref=turn_refs[-1] if turn_refs else None,
                verdict=final_verdict.value,
                paused=True,
            )
            outcome = wait_for_resume_or_stop(
                config.run_id,
                max_wait_seconds=min(300.0, float(config.max_duration_seconds)),
                base=extended_base,
                pause_path=config.pause_file_path,
                resume_path=config.resume_file_path,
                check_stop=_stop,
                check_panic=_panic,
            )
            if outcome == "panic":
                panic_events += 1
                final_status = ExtendedDryAutonomyState.PANIC
                final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_STOPPED_BY_OPERATOR
                break
            if outcome == "stop":
                stop_events += 1
                final_status = ExtendedDryAutonomyState.STOPPED
                final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_STOPPED_BY_OPERATOR
                break
            if outcome == "resume":
                latest = load_checkpoint(config.run_id, extended_base=extended_base)
                if not latest:
                    budget.record_pause_resume_failure()
                    final_status = ExtendedDryAutonomyState.FAILED
                    final_verdict = ExtendedDryAutonomyVerdict.RED_EXTENDED_DRY_AUTONOMY_RESUME_FAILURE
                    break
                try:
                    resume_from_checkpoint(latest, extended_base=extended_base, turn_base=tbase, agent_id=config.agent_id)
                    rs = record_resume_event(
                        config.run_id,
                        checkpoint_id=latest.checkpoint_id,
                        base=extended_base,
                        resume_path=config.resume_file_path,
                    )
                    pause_resume_events.extend(rs.events)
                    resumed_once = True
                except Exception:
                    budget.record_pause_resume_failure()
                    final_status = ExtendedDryAutonomyState.FAILED
                    final_verdict = ExtendedDryAutonomyVerdict.RED_EXTENDED_DRY_AUTONOMY_RESUME_FAILURE
                    break
            else:
                stop_events += 1
                final_status = ExtendedDryAutonomyState.STOPPED
                final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_STOPPED_BY_OPERATOR
                break

        sched.iteration += 1
        heartbeat_lock(config.run_id, base=extended_base)
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
            budget.record_red_turn()
            release_lock(config.run_id, status="failed", base=extended_base)
            lock_released = True
            raise ExtendedDryAutonomyRunnerError(f"RED_EXTENDED_DRY_AUTONOMY_RECEIPT_GAP:{outcome.verdict.value}")

        if not outcome.turn_receipt_ref:
            budget.record_missing_receipt()
            release_lock(config.run_id, status="failed", base=extended_base)
            lock_released = True
            raise ExtendedDryAutonomyRunnerError("RED_EXTENDED_DRY_AUTONOMY_RECEIPT_GAP")

        if outcome.verdict in (
            AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_PROVIDER_UNAVAILABLE,
            AgentTurnVerdict.YELLOW_AGENT_TURN_RESTED,
            AgentTurnVerdict.YELLOW_AGENT_TURN_WITNESS_ONLY,
        ):
            if not config.allow_provider:
                if final_verdict == ExtendedDryAutonomyVerdict.GREEN_EXTENDED_DRY_AUTONOMY_COMPLETE:
                    final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_PROVIDER_UNAVAILABLE

        if outcome.verdict == AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_LIVE_READ_UNAVAILABLE:
            if not config.allow_live_read and final_verdict == ExtendedDryAutonomyVerdict.GREEN_EXTENDED_DRY_AUTONOMY_COMPLETE:
                final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_LIVE_READ_UNAVAILABLE

        resource_snap = collect_resource_snapshot(
            run_id=config.run_id,
            turn_index=outcome.turn_index,
            turn_duration_seconds=time.monotonic() - turn_start,
            turn_base=tbase,
            dry_soak_root=extended_base or run_dir.parent,
        )
        last_artifact_count = resource_snap.artifact_count
        last_review_count = resource_snap.review_queue_count
        budget.record_queue_growth(resource_snap.review_queue_count)
        resource_throttled = resource_snap.verdict == "YELLOW_DRY_SOAK_RESOURCE_PRESSURE"
        if resource_throttled:
            final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_RESOURCE_THROTTLED

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
        except EnduranceBudgetExceeded as exc:
            final_status = ExtendedDryAutonomyState.FAILED
            final_verdict = ExtendedDryAutonomyVerdict(exc.verdict)
            break

        store.append_iteration(
            {
                "iteration_index": sched.iteration,
                "turn_receipt_ref": outcome.turn_receipt_ref,
                "turn_verdict": outcome.verdict.value,
                "artifact_count": last_artifact_count,
                "review_queue_count": last_review_count,
                "created_at": outcome.created_at,
            }
        )
        turn_refs.append(outcome.turn_receipt_ref)

        hb = build_extended_heartbeat(
            run_id=config.run_id,
            iteration_index=sched.iteration,
            elapsed_seconds=sched.elapsed_seconds(),
            provider_status=provider_status,
            live_read_status=live_read_status,
            live_read_receipt_ref=live_read_receipt_ref,
            provider_health_receipt_ref=provider_health_receipt_ref,
            provider_kind=provider_kind,
            model_id=model_id,
            artifact_count=last_artifact_count,
            review_queue_count=last_review_count,
            last_turn_ref=outcome.turn_receipt_ref,
            last_turn_verdict=outcome.verdict.value,
            endurance_budget_status=budget.verdict,
            resource_status=resource_snap.verdict,
            duplication_status=dup_report.verdict,
            verdict=final_verdict.value,
            extended_base=extended_base,
            checkpoint_status="written" if checkpoint_refs else "none",
        )
        store.append_heartbeat(hb)
        heartbeat_refs.append(hb["heartbeat_id"])
        write_exciton_snapshot(config.run_id, hb, config=config.to_payload(), extended_base=extended_base)

        store.write_state_snapshot(
            status=ExtendedDryAutonomyState.RUNNING,
            iteration_count=sched.iteration,
            last_turn_ref=outcome.turn_receipt_ref,
            verdict=final_verdict.value,
        )

        elapsed = sched.elapsed_seconds()
        if _should_checkpoint(sched.iteration, elapsed, config, last_checkpoint_iter, last_checkpoint_mono):
            cp = write_checkpoint(
                run_id=config.run_id,
                iteration_index=sched.iteration,
                turn_result_ref=outcome.turn_receipt_ref,
                heartbeat_hash=hash_record(hb),
                boot_anchor_ref=boot_ref,
                extended_base=extended_base,
                turn_base=tbase,
            )
            checkpoint_refs.append(cp.checkpoint_id)
            last_checkpoint_iter = sched.iteration
            last_checkpoint_mono = time.monotonic()

        if _panic():
            panic_events += 1
            final_status = ExtendedDryAutonomyState.PANIC
            final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_STOPPED_BY_OPERATOR
            break
        if _stop():
            stop_events += 1
            final_status = ExtendedDryAutonomyState.STOPPED
            final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_STOPPED_BY_OPERATOR
            break

        if sched.iteration < config.max_iterations and should_continue(sched, sched_cfg):
            sleep_secs = compute_sleep_seconds(sched_cfg, resource_throttled=resource_throttled)
            sleep_secs = adjusted_turn_interval(sleep_secs, resource_snap)
            if sleep_bounded(sleep_secs, sched_cfg, check_stop=_stop, check_panic=_panic):
                if _panic():
                    panic_events += 1
                    final_status = ExtendedDryAutonomyState.PANIC
                    final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_STOPPED_BY_OPERATOR
                else:
                    stop_events += 1
                    final_status = ExtendedDryAutonomyState.STOPPED
                    final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_STOPPED_BY_OPERATOR
                break

    if resumed_once and final_verdict == ExtendedDryAutonomyVerdict.GREEN_EXTENDED_DRY_AUTONOMY_COMPLETE:
        final_verdict = ExtendedDryAutonomyVerdict.YELLOW_EXTENDED_DRY_AUTONOMY_PAUSED_AND_RESUMED

    finished_at = now_iso()
    if not lock_released:
        release_lock(config.run_id, status=final_status.value, base=extended_base)

    panic_anchor = None
    if panic_events > 0:
        shutdown_anchor = record_loop_shutdown_anchor(
            run_id=config.run_id,
            agent_id=config.agent_id,
            verdict=final_verdict.value,
            iteration_count=sched.iteration,
            panic=True,
        )
        panic_anchor = shutdown_anchor
    else:
        shutdown_anchor = record_loop_shutdown_anchor(
            run_id=config.run_id,
            agent_id=config.agent_id,
            verdict=final_verdict.value,
            iteration_count=sched.iteration,
            panic=False,
        )
    shutdown_ref = shutdown_anchor.get("journal_receipt_id") or shutdown_anchor.get("receipt_id")

    anchor_audit = audit_lifecycle_anchors(
        run_id=config.run_id,
        boot_anchor=boot_anchor,
        shutdown_anchor=shutdown_anchor if panic_events == 0 else None,
        panic_anchor=panic_anchor,
        remote_anchor_push_allowed=config.remote_anchor_push_allowed,
    )
    if anchor_audit.verdict == "RED_EXTENDED_DRY_AUTONOMY_REMOTE_ANCHOR_FALSE_GREEN":
        budget.record_remote_anchor_false_green()
    write_json(run_dir / "anchor_audit.json", anchor_audit.to_payload())

    postflight = run_extended_postflight(
        run_id=config.run_id,
        agent_id=config.agent_id,
        started_at=started_at,
        iteration_count=sched.iteration,
        stop_events=stop_events,
        panic_events=panic_events,
        pause_events=pause_events,
        extended_base=extended_base,
        turn_base=tbase,
        boot_anchor=boot_anchor,
        shutdown_anchor=shutdown_anchor,
        anchor_audit_verdict=anchor_audit.verdict,
    )

    run = ExtendedDryAutonomyRun(
        run_id=config.run_id,
        agent_id=config.agent_id,
        started_at=started_at,
        finished_at=finished_at,
        status=final_status,
        config_hash=config.hash,
        lock_ref=str(current_lock_path(base=extended_base)),
        iteration_count=sched.iteration,
        turn_result_refs=turn_refs,
        heartbeat_refs=heartbeat_refs,
        checkpoint_refs=checkpoint_refs,
        pause_resume_events=pause_resume_events,
        stop_panic_events=[
            *([{"kind": "stop", "at": finished_at}] if stop_events else []),
            *([{"kind": "panic", "at": finished_at}] if panic_events else []),
        ],
        postflight_ref=str(run_dir / "postflight.json"),
        anchor_audit_ref=str(run_dir / "anchor_audit.json"),
        verdict=final_verdict,
        boot_anchor_ref=boot_ref,
        shutdown_anchor_ref=shutdown_ref,
    ).with_hash()

    readiness = ReadinessVerdict.GREEN_READY_FOR_PHASE_15_LIVE_PROVIDER_DRY_AUTONOMY
    if not config.allow_provider:
        readiness = ReadinessVerdict.YELLOW_READY_FOR_LOCAL_ONLY_DRY_AUTONOMY
    if final_verdict.value.startswith("RED_"):
        readiness = ReadinessVerdict.RED_NOT_READY_FOR_PHASE_15
    run.readiness_verdict = readiness.value

    store.write_run(run.to_payload())
    build_endurance_report(
        run=run,
        config=config,
        postflight=postflight,
        anchor_audit=anchor_audit,
        budget=budget,
        duration_seconds=_elapsed_seconds(started_at),
        provider_status=provider_status,
        live_read_status=live_read_status,
        readiness=readiness,
        extended_base=extended_base,
    )

    return run.with_hash()


__all__ = ["run_extended_dry_autonomy"]
