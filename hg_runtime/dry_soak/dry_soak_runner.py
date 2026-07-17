"""Longer supervised dry soak runner — bounded, not autonomous."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.agent_turn_engine.engine import run_single_agent_turn
from hg_runtime.agent_turn_engine.schema import AgentTurnFailure, AgentTurnResult, AgentTurnVerdict, build_agent_turn_request
from hg_runtime.agent_turn_engine.turn_storage import turns_root
from hg_runtime.dry_soak.duplication_watchdog import analyze_duplication
from hg_runtime.dry_soak.errors import DrySoakRunnerError, FailureBudgetExceeded
from hg_runtime.supervised_rehearsal.errors import RehearsalLockError
from hg_runtime.dry_soak.exciton_snapshot import build_exciton_dry_soak_snapshot
from hg_runtime.dry_soak.failure_budget import FailureBudgetState, new_failure_budget_state
from hg_runtime.dry_soak.readiness_report import (
    build_readiness_report,
    persist_readiness_report,
    write_readiness_report_md,
)
from hg_runtime.dry_soak.resource_watchdog import adjusted_turn_interval, collect_resource_snapshot
from hg_runtime.dry_soak.schema import (
    DrySoakConfig,
    DrySoakRun,
    DrySoakRunStatus,
    DrySoakTurnSummary,
    DrySoakVerdict,
    now_iso,
    validate_dry_soak_config,
)
from hg_runtime.dry_soak.storage import dry_soak_root, run_dry_soak_dir, write_json
from hg_runtime.supervised_rehearsal.postflight import run_postflight
from hg_runtime.supervised_rehearsal.run_lock import acquire_lock, heartbeat_lock, release_lock
from hg_runtime.supervised_rehearsal.stop_panic import (
    check_panic,
    check_stop,
    ensure_stop_panic_available,
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


def run_longer_supervised_dry_soak(
    config: DrySoakConfig,
    *,
    soak_base: Path | None = None,
    turn_base: Path | None = None,
    provider_invoke=None,
) -> DrySoakRun:
    """Run bounded longer dry soak — not unbounded autonomy."""
    config = validate_dry_soak_config(config)
    base = soak_base or dry_soak_root()
    run_dir = run_dry_soak_dir(config.run_id, base=base)
    run_dir.mkdir(parents=True, exist_ok=True)

    if not config.stop_file_path:
        config = DrySoakConfig(**{**config.__dict__, "stop_file_path": str(run_dir / "STOP")})
    if not config.panic_file_path:
        config = DrySoakConfig(**{**config.__dict__, "panic_file_path": str(run_dir / "PANIC")})

    write_json(run_dir / "config.json", config.to_payload())
    try:
        acquire_lock(config.run_id, base=base)
    except RehearsalLockError as exc:
        raise DrySoakRunnerError(f"RED_DRY_SOAK_LOCK_FAILURE:{exc}") from exc
    ensure_stop_panic_available(
        config.run_id,
        base=base,
        stop_path=config.stop_file_path,
        panic_path=config.panic_file_path,
    )

    tbase = _turn_base(turn_base=turn_base)
    budget = new_failure_budget_state()
    started_at = now_iso()
    summaries: list[DrySoakTurnSummary] = []
    deferred_turns = 0
    stop_events = 0
    panic_events = 0
    final_status = DrySoakRunStatus.COMPLETED
    final_verdict = DrySoakVerdict.GREEN_DRY_SOAK_COMPLETE
    last_resource_verdict = "GREEN_RESOURCE_OK"
    last_dup_verdict = "GREEN_DUPLICATION_OK"
    last_heartbeat = started_at
    provider_status = "available" if config.allow_provider else "unavailable"
    live_read_status = "available" if config.allow_live_read else "unavailable"
    last_artifact_count = 0
    last_review_count = 0
    budget_failure: str | None = None
    lock_released = False

    turn_num = 0
    while turn_num < config.max_turns:
        turn_num += 1
        elapsed = _elapsed_seconds(started_at)

        if check_panic(config.run_id, panic_path=config.panic_file_path):
            panic_events += 1
            final_status = DrySoakRunStatus.PANIC
            final_verdict = DrySoakVerdict.YELLOW_DRY_SOAK_STOPPED_BY_OPERATOR
            break

        if turn_num > 1 and check_stop(config.run_id, stop_path=config.stop_file_path):
            stop_events += 1
            final_status = DrySoakRunStatus.STOPPED
            final_verdict = DrySoakVerdict.YELLOW_DRY_SOAK_STOPPED_BY_OPERATOR
            break

        if elapsed >= config.max_duration_seconds:
            break

        if turn_num > config.target_turns and elapsed >= config.target_duration_seconds:
            break

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

        turn_duration = time.monotonic() - turn_start

        if isinstance(outcome, AgentTurnFailure) or (
            isinstance(outcome, AgentTurnResult) and outcome.verdict.value.startswith("RED_")
        ):
            try:
                budget.record_red_turn()
            except FailureBudgetExceeded as exc:
                budget_failure = exc.verdict
                final_status = DrySoakRunStatus.FAILED
                final_verdict = DrySoakVerdict(exc.verdict)
                break
            release_lock(config.run_id, status="failed", base=base)
            lock_released = True
            verdict = outcome.verdict.value
            raise DrySoakRunnerError(f"RED_DRY_SOAK_RECEIPT_GAP:{verdict}")

        if not outcome.turn_receipt_ref:
            try:
                budget.record_missing_receipt()
            except FailureBudgetExceeded as exc:
                budget_failure = exc.verdict
                final_status = DrySoakRunStatus.FAILED
                final_verdict = DrySoakVerdict(exc.verdict)
                break
            release_lock(config.run_id, status="failed", base=base)
            lock_released = True
            raise DrySoakRunnerError("RED_DRY_SOAK_RECEIPT_GAP")

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

        resource_snap = None
        dup_report = None
        if config.resource_watchdog_enabled:
            try:
                resource_snap = collect_resource_snapshot(
                    run_id=config.run_id,
                    turn_index=outcome.turn_index,
                    turn_duration_seconds=turn_duration,
                    turn_base=tbase,
                    dry_soak_root=base,
                )
                last_resource_verdict = resource_snap.verdict
                last_artifact_count = resource_snap.artifact_count
                last_review_count = resource_snap.review_queue_count
                budget.record_queue_growth(resource_snap.review_queue_count)
                write_json(run_dir / f"resource-{turn_num:04d}.json", resource_snap.to_payload())
                if resource_snap.verdict == "YELLOW_DRY_SOAK_RESOURCE_PRESSURE":
                    final_verdict = DrySoakVerdict.YELLOW_DRY_SOAK_RESOURCE_PRESSURE
            except FailureBudgetExceeded as exc:
                budget_failure = exc.verdict
                final_status = DrySoakRunStatus.FAILED
                final_verdict = DrySoakVerdict(exc.verdict)
                break

        if config.duplication_watchdog_enabled:
            try:
                dup_report = analyze_duplication(
                    run_id=config.run_id,
                    turn_index=outcome.turn_index,
                    turn_verdict=outcome.verdict.value,
                    turn_base=tbase,
                )
                last_dup_verdict = dup_report.verdict
                budget.record_duplicate_rate(dup_report.duplicate_body_hash_rate)
                write_json(run_dir / f"duplication-{turn_num:04d}.json", dup_report.to_payload())
                if dup_report.verdict.startswith("RED_"):
                    if "FIXTURE" in dup_report.verdict:
                        budget.record_fixture_truth()
                    else:
                        budget.record_duplicate_rate(1.0)
            except FailureBudgetExceeded as exc:
                budget_failure = exc.verdict
                final_status = DrySoakRunStatus.FAILED
                final_verdict = DrySoakVerdict(exc.verdict)
                break

        summary = DrySoakTurnSummary(
            turn_index=outcome.turn_index,
            turn_receipt_ref=outcome.turn_receipt_ref,
            verdict=outcome.verdict.value,
            artifact_count=last_artifact_count,
            review_queue_count=last_review_count,
            created_at=outcome.created_at,
        )
        summaries.append(summary)
        with (run_dir / "turn_summaries.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(summary.to_payload(), sort_keys=True) + "\n")

        last_heartbeat = now_iso()
        exciton_snap = build_exciton_dry_soak_snapshot(
            run_id=config.run_id,
            run_status=final_status.value,
            turn_count=len(summaries),
            elapsed_seconds=_elapsed_seconds(started_at),
            provider_status=provider_status,
            live_read_status=live_read_status,
            artifact_count=last_artifact_count,
            review_queue_count=last_review_count,
            duplication_report=dup_report,
            resource_snapshot=resource_snap,
            budget_state=budget,
            dry_soak_verdict=final_verdict.value,
            last_heartbeat_at=last_heartbeat,
            dry_soak_base=base,
        )
        write_json(run_dir / "exciton_snapshot.json", exciton_snap)

        interval = config.turn_interval_seconds
        if resource_snap:
            interval = adjusted_turn_interval(interval, resource_snap)
        if interval > 0 and turn_num < config.max_turns:
            time.sleep(interval)

    if deferred_turns and final_verdict == DrySoakVerdict.GREEN_DRY_SOAK_COMPLETE:
        if not config.allow_provider:
            final_verdict = DrySoakVerdict.YELLOW_DRY_SOAK_COMPLETED_WITH_PROVIDER_UNAVAILABLE
        elif deferred_turns == len(summaries):
            final_verdict = DrySoakVerdict.YELLOW_DRY_SOAK_NO_ARTIFACTS_CREATED

    if not config.allow_live_read and deferred_turns:
        if final_verdict == DrySoakVerdict.GREEN_DRY_SOAK_COMPLETE:
            final_verdict = DrySoakVerdict.YELLOW_DRY_SOAK_COMPLETED_WITH_LIVE_READ_UNAVAILABLE

    finished_at = now_iso()

    if not lock_released:
        release_lock(config.run_id, status=final_status.value, base=base)

    postflight = run_postflight(
        run_id=config.run_id,
        agent_id=config.agent_id,
        started_at=started_at,
        turn_count=len(summaries),
        stop_events=stop_events,
        panic_events=panic_events,
        rehearsal_base=base,
        turn_base=tbase,
    )

    if postflight.external_side_effects:
        budget.record_external_side_effect()

    run = DrySoakRun(
        run_id=config.run_id,
        agent_id=config.agent_id,
        started_at=started_at,
        finished_at=finished_at,
        status=final_status,
        config_hash=config.hash,
        turn_count=len(summaries),
        turn_summaries=summaries,
        verdict=final_verdict,
    ).with_hash()

    readiness = build_readiness_report(
        run=run,
        duration_seconds=_elapsed_seconds(started_at),
        provider_status=provider_status,
        live_read_status=live_read_status,
        replay_status=postflight.replay_verdict,
        artifact_count=postflight.artifact_count,
        review_queue_count=postflight.review_candidate_count,
        duplication_verdict=last_dup_verdict,
        resource_verdict=last_resource_verdict,
        failure_budget_verdict=budget.verdict,
        external_side_effects=postflight.external_side_effects,
        target_duration_seconds=config.target_duration_seconds,
    )
    run.readiness_verdict = readiness.readiness_verdict.value
    run = run.with_hash()

    write_json(run_dir / "run.json", run.to_payload())
    persist_readiness_report(readiness, run_id=config.run_id, base=base)
    write_readiness_report_md(readiness, run=run)

    return run


__all__ = ["run_longer_supervised_dry_soak"]
