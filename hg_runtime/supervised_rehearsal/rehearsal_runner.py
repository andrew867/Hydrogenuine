"""Supervised short-run rehearsal runner — bounded, not autonomous."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.agent_turn_engine.engine import run_single_agent_turn
from hg_runtime.agent_turn_engine.schema import AgentTurnFailure, AgentTurnResult, AgentTurnVerdict, build_agent_turn_request
from hg_runtime.agent_turn_engine.turn_storage import turns_root
from hg_runtime.supervised_rehearsal.errors import RehearsalRunnerError
from hg_runtime.supervised_rehearsal.observer import build_observer_heartbeat, write_observer_heartbeat
from hg_runtime.supervised_rehearsal.postflight import run_postflight
from hg_runtime.supervised_rehearsal.rehearsal_store import RehearsalStore
from hg_runtime.supervised_rehearsal.run_lock import acquire_lock, heartbeat_lock, release_lock
from hg_runtime.supervised_rehearsal.schema import (
    RehearsalRunStatus,
    SupervisedRehearsalConfig,
    SupervisedRehearsalResult,
    SupervisedRehearsalRun,
    SupervisedRehearsalTurnSummary,
    SupervisedRehearsalVerdict,
    now_iso,
    validate_rehearsal_config,
)
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


def _turn_base(config: SupervisedRehearsalConfig, *, turn_base: Path | None = None) -> Path:
    if turn_base:
        return turn_base
    env = os.environ.get("HG_AGENT_TURN_BASE")
    if env:
        return Path(env)
    return turns_root()


def run_supervised_rehearsal(
    config: SupervisedRehearsalConfig,
    *,
    rehearsal_base: Path | None = None,
    turn_base: Path | None = None,
    provider_invoke=None,
) -> SupervisedRehearsalResult:
    """Run bounded supervised rehearsal — not an unbounded autonomous loop."""
    config = validate_rehearsal_config(config)
    store = RehearsalStore(config.run_id, base=rehearsal_base)
    store.root.mkdir(parents=True, exist_ok=True)
    store.store_config(config)

    lock = acquire_lock(config.run_id, base=rehearsal_base)
    lock_ref = f"lock-{config.run_id}"

    sp = ensure_stop_panic_available(
        config.run_id,
        base=rehearsal_base,
        stop_path=config.stop_file_path,
        panic_path=config.panic_file_path,
    )

    started_at = now_iso()
    run = SupervisedRehearsalRun(
        run_id=config.run_id,
        agent_id=config.agent_id,
        started_at=started_at,
        status=RehearsalRunStatus.RUNNING,
        config_hash=config.hash,
        lock_ref=lock_ref,
        turn_count=0,
        turn_result_refs=[],
        stop_panic_events=[],
        verdict=SupervisedRehearsalVerdict.GREEN_SUPERVISED_REHEARSAL_COMPLETE,
    ).with_hash()
    store.store_run(run)

    tbase = _turn_base(config, turn_base=turn_base)
    summaries: list[SupervisedRehearsalTurnSummary] = []
    turn_result_refs: list[str] = []
    deferred_turns = 0
    stop_events = 0
    panic_events = 0
    final_status = RehearsalRunStatus.COMPLETED
    final_verdict = SupervisedRehearsalVerdict.GREEN_SUPERVISED_REHEARSAL_COMPLETE

    hb = build_observer_heartbeat(
        run_id=config.run_id,
        heartbeat_index=0,
        turn_count=0,
        current_stage="initialized",
        base=rehearsal_base,
        stop_path=config.stop_file_path,
        panic_path=config.panic_file_path,
    )
    write_observer_heartbeat(store, hb)

    for turn_num in range(1, config.max_turns + 1):
        if check_panic(config.run_id, base=rehearsal_base, panic_path=config.panic_file_path):
            panic_events += 1
            run.stop_panic_events.append({"kind": "panic", "at": now_iso(), "turn": turn_num})
            final_status = RehearsalRunStatus.PANIC
            final_verdict = SupervisedRehearsalVerdict.YELLOW_REHEARSAL_STOPPED_BY_OPERATOR
            break

        if turn_num > 1 and check_stop(config.run_id, base=rehearsal_base, stop_path=config.stop_file_path):
            stop_events += 1
            run.stop_panic_events.append({"kind": "stop", "at": now_iso(), "turn": turn_num})
            final_status = RehearsalRunStatus.STOPPED
            final_verdict = SupervisedRehearsalVerdict.YELLOW_REHEARSAL_STOPPED_BY_OPERATOR
            break

        if _elapsed_seconds(started_at) >= config.max_duration_seconds:
            final_verdict = SupervisedRehearsalVerdict.YELLOW_REHEARSAL_COMPLETED_WITH_DEFERRED_TURNS
            break

        heartbeat_lock(config.run_id, base=rehearsal_base)

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

        if isinstance(outcome, AgentTurnFailure):
            release_lock(config.run_id, status="failed", base=rehearsal_base)
            raise RehearsalRunnerError(f"RED_REHEARSAL_TURN_FAILURE:{outcome.verdict.value}")

        if outcome.verdict.value.startswith("RED_"):
            release_lock(config.run_id, status="failed", base=rehearsal_base)
            raise RehearsalRunnerError(f"RED_REHEARSAL_TURN_FAILURE:{outcome.verdict.value}")

        if outcome.verdict in (
            AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_PROVIDER_UNAVAILABLE,
            AgentTurnVerdict.YELLOW_AGENT_TURN_RESTED,
            AgentTurnVerdict.YELLOW_AGENT_TURN_WITNESS_ONLY,
        ):
            deferred_turns += 1

        summary = SupervisedRehearsalTurnSummary(
            turn_index=outcome.turn_index,
            turn_receipt_ref=outcome.turn_receipt_ref,
            turn_result_ref=outcome.result_id,
            verdict=outcome.verdict.value,
            observe_snapshot_ref=outcome.observe_snapshot_ref,
            broker_decision_ref=outcome.broker_decision_ref,
            created_at=outcome.created_at,
        )
        summaries.append(summary)
        turn_result_refs.append(outcome.result_id)
        store.append_turn_summary(summary.to_payload())

        hb = build_observer_heartbeat(
            run_id=config.run_id,
            heartbeat_index=turn_num,
            turn_count=turn_num,
            current_stage="turn_complete",
            last_turn_ref=outcome.turn_receipt_ref,
            provider_status="available" if config.allow_provider else "unavailable",
            live_read_status="available" if config.allow_live_read else "unavailable",
            base=rehearsal_base,
            stop_path=config.stop_file_path,
            panic_path=config.panic_file_path,
        )
        write_observer_heartbeat(store, hb)

        if config.turn_interval_seconds > 0 and turn_num < config.max_turns:
            time.sleep(config.turn_interval_seconds)

    if deferred_turns and final_verdict == SupervisedRehearsalVerdict.GREEN_SUPERVISED_REHEARSAL_COMPLETE:
        final_verdict = SupervisedRehearsalVerdict.YELLOW_REHEARSAL_COMPLETED_WITH_DEFERRED_TURNS
    if not config.allow_provider and deferred_turns:
        if final_verdict == SupervisedRehearsalVerdict.GREEN_SUPERVISED_REHEARSAL_COMPLETE:
            final_verdict = SupervisedRehearsalVerdict.YELLOW_REHEARSAL_PROVIDER_UNAVAILABLE

    finished_at = now_iso()
    release_lock(config.run_id, status=final_status.value, base=rehearsal_base)

    postflight = run_postflight(
        run_id=config.run_id,
        agent_id=config.agent_id,
        started_at=started_at,
        turn_count=len(summaries),
        stop_events=stop_events,
        panic_events=panic_events,
        rehearsal_base=rehearsal_base,
        turn_base=tbase,
    )

    run.finished_at = finished_at
    run.turn_count = len(summaries)
    run.turn_result_refs = turn_result_refs
    run.status = final_status
    run.verdict = final_verdict
    store.store_run(run.with_hash())

    result = SupervisedRehearsalResult(
        run_id=config.run_id,
        agent_id=config.agent_id,
        started_at=started_at,
        finished_at=finished_at,
        turn_count=len(summaries),
        turn_summaries=summaries,
        postflight_ref=str(store.postflight_path),
        verdict=final_verdict,
        run_status=final_status.value,
        deferred_turns=deferred_turns,
    ).with_hash()
    store.store_result(result)
    return result


__all__ = ["run_supervised_rehearsal"]
