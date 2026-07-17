"""Foreground hands-off session runner — unlimited turns, manual stop."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from hg_runtime.agent_turn_engine.engine import run_single_agent_turn
from hg_runtime.agent_turn_engine.schema import AgentTurnFailure, AgentTurnResult, AgentTurnVerdict, build_agent_turn_request
from hg_runtime.agent_turn_engine.turn_storage import turns_root
from hg_runtime.hands_off_session.errors import HandsOffBudgetError, HandsOffConfigError, HandsOffLockError, HandsOffSessionError
from hg_runtime.hands_off_session.heartbeat import write_heartbeat
from hg_runtime.hands_off_session.manual_controls import check_panic, check_stop, ensure_controls_available
from hg_runtime.hands_off_session.postflight import SessionPostflight, write_postflight
from hg_runtime.hands_off_session.schema import (
    HandsOffSessionStatus,
    HandsOffSessionVerdict,
    STORE_ROOT,
    now_iso,
    session_dir,
)
from hg_runtime.hands_off_session.session_config import HandsOffSessionConfig, validate_session_config
from hg_runtime.hands_off_session.session_lock import acquire_lock, heartbeat_lock, release_lock
from hg_runtime.hands_off_session.session_receipts import ContinuousTurnReceipt, persist_continuous_turn_receipt, persist_start_receipt
from hg_runtime.hands_off_session.session_state import HandsOffSessionState, persist_state
from hg_runtime.hands_off_session.watchdog_budget import default_watchdog_budget
from hg_runtime.task_selection.objective_universe import create_demo_universe, list_universes, load_universe
from hg_runtime.task_selection.schema import AllowedTaskType, TaskSelectionVerdict
from hg_runtime.task_selection.task_candidate import load_candidate, seed_demo_candidates
from hg_runtime.task_selection.task_selector import TaskSelectionContext, select_next_task


def _live_posts_allowed(soak_id: str) -> bool:
    from hg_runtime.real_soak_launch.moltbook_envelope import load_armed_envelope

    env_ok = (
        os.environ.get("HG_SOCIAL_LIVE_PUBLISH", "false").lower() == "true"
        or os.environ.get("HG_ENABLE_LIVE_SOCIAL_WRITES", "false").lower() == "true"
    )
    armed = load_armed_envelope(soak_id)
    return bool(env_ok and armed and armed.max_live_posts > 0 and armed.is_armed() and not armed.is_expired())


def _load_candidates_for_universe(universe_id: str) -> list:
    from hg_runtime.task_selection.schema import STORE_ROOT as TS_ROOT

    cand_dir = TS_ROOT / "candidates"
    candidates = []
    if cand_dir.is_dir():
        for p in sorted(cand_dir.glob("*.json")):
            c = load_candidate(p.stem)
            if c and (not c.source_ref or universe_id in (c.source_ref or "")):
                candidates.append(c)
    if not candidates:
        candidates = seed_demo_candidates(universe_id)
    return candidates


def _resolve_universe(config: HandsOffSessionConfig):
    if config.objective_universe_ref:
        u = load_universe(config.objective_universe_ref)
        if u:
            return u
    universes = list_universes()
    if universes:
        return universes[-1]
    return create_demo_universe(agent_id=config.agent_id)


def _fast_turn_result(request) -> AgentTurnResult:
    from hg_runtime.agent_turn_engine.schema import AgentTurnVerdict, new_result_id

    return AgentTurnResult(
        result_id=new_result_id(),
        request_id=request.request_id,
        agent_id=request.agent_id,
        run_id=request.run_id,
        turn_index=1,
        agent_state_ref="fast-state",
        observe_snapshot_ref="fast-observe",
        capability_menu_ref="fast-menu",
        broker_decision_ref="fast-broker",
        turn_receipt_ref=f"fast-receipt-{request.run_id}",
        journal_ref="fast-journal",
        state_after_ref="fast-state-after",
        verdict=AgentTurnVerdict.GREEN_AGENT_TURN_COMPLETE_INTERNAL,
        created_at=now_iso(),
    )


def _turn_executor(request, *, turn_base: Path | None = None):
    if os.environ.get("HG_HANDS_OFF_FAST_TURNS") == "1":
        return _fast_turn_result(request)
    return run_single_agent_turn(request, base=turn_base)


def run_hands_off_session(
    config: HandsOffSessionConfig,
    *,
    base: Path | None = None,
    turn_base: Path | None = None,
    production_mode: bool = True,
) -> SessionPostflight:
    """Run foreground hands-off session until STOP/PANIC/budget/failure."""
    store_base = base or STORE_ROOT
    config = validate_session_config(config, production_mode=production_mode)
    session_root = session_dir(config.session_id, base=store_base)
    session_root.mkdir(parents=True, exist_ok=True)
    (session_root / "config.json").write_text(json.dumps(config.to_payload(), indent=2) + "\n", encoding="utf-8")

    try:
        acquire_lock(config.session_id, base=store_base)
    except HandsOffLockError as exc:
        raise HandsOffSessionError(str(exc)) from exc

    ensure_controls_available(config.session_id, base=store_base)
    persist_start_receipt(config.session_id, config.hash or "", base=store_base)

    pid = os.getpid()
    started_at = now_iso()
    state = HandsOffSessionState(
        session_id=config.session_id,
        pid=pid,
        status=HandsOffSessionStatus.STARTING.value,
        started_at=started_at,
    ).with_hash()
    persist_state(state, base=store_base)

    budget = default_watchdog_budget()
    if config.external_side_effects_allowed:
        soak_id = os.environ.get("HG_REAL_SOAK_SOAK_ID")
        max_posts = 1
        if soak_id:
            from hg_runtime.real_soak_launch.moltbook_envelope import load_armed_envelope

            armed = load_armed_envelope(soak_id)
            if armed and armed.max_live_posts > 0:
                max_posts = armed.max_live_posts
        budget.max_external_side_effects = max_posts
    final_verdict = HandsOffSessionVerdict.GREEN_SESSION_COMPLETE
    stop_requested = False
    panic_requested = False
    tbase = turn_base or turns_root()
    if os.environ.get("HG_AGENT_TURN_BASE"):
        tbase = Path(os.environ["HG_AGENT_TURN_BASE"])

    universe = _resolve_universe(config)
    if not config.objective_universe_ref:
        config = HandsOffSessionConfig(**{**config.__dict__, "objective_universe_ref": universe.universe_id})

    hb = write_heartbeat(
        session_id=config.session_id,
        pid=pid,
        turn_count=0,
        status=HandsOffSessionStatus.RUNNING.value,
        base=store_base,
    )
    state = HandsOffSessionState(
        **{**state.__dict__, "status": HandsOffSessionStatus.RUNNING.value, "last_heartbeat_ref": hb.heartbeat_id}
    ).with_hash()
    persist_state(state, base=store_base)
    heartbeat_lock(config.session_id, base=store_base)

    observed_turns = 0
    test_limit = config.test_only_stop_after_observed_turns
    completed_candidates: set[str] = set()

    while True:
        if check_panic(config.session_id, base=store_base):
            panic_requested = True
            final_verdict = HandsOffSessionVerdict.YELLOW_STOPPED_BY_OPERATOR
            break

        if observed_turns > 0 and check_stop(config.session_id, base=store_base):
            stop_requested = True
            final_verdict = HandsOffSessionVerdict.YELLOW_STOPPED_BY_OPERATOR
            break

        if test_limit is not None and observed_turns >= test_limit:
            stop_requested = True
            final_verdict = HandsOffSessionVerdict.YELLOW_STOPPED_BY_OPERATOR
            break

        candidates = [c for c in _load_candidates_for_universe(universe.universe_id) if c.task_candidate_id not in completed_candidates]
        if not candidates:
            candidates = seed_demo_candidates(universe.universe_id)
            completed_candidates.clear()
        ts_ctx = TaskSelectionContext(
            universe=universe,
            candidates=candidates,
            run_id=config.session_id,
            stop_panic_clear=not check_panic(config.session_id, base=store_base),
        )
        ts_result = select_next_task(ts_ctx)

        if ts_result.receipt is None and config.manual_stop_required:
            budget.missing_receipts += 1
            budget._enforce()

        if ts_result.verdict in (
            TaskSelectionVerdict.GREEN_IDLE_REFLECTION,
            TaskSelectionVerdict.YELLOW_OBJECTIVE_QUEUE_EMPTY,
        ):
            state.idle_count += 1
            state = HandsOffSessionState(**{**state.__dict__, "idle_count": state.idle_count}).with_hash()
            persist_state(state, base=store_base)
            if ts_result.receipt:
                state.last_task_selection_ref = ts_result.receipt.task_selection_receipt_id
            time.sleep(config.turn_interval_seconds)
            continue

        if ts_result.selected is None:
            if ts_result.verdict.value.startswith("RED_"):
                final_verdict = HandsOffSessionVerdict.RED_TASK_SELECTION_WITHOUT_RECEIPT
                break
            time.sleep(config.turn_interval_seconds)
            continue

        state.selected_task_count += 1
        completed_candidates.add(ts_result.selected.task_candidate_id)
        budget.record_task_selection(ts_result.selected.task_candidate_id)

        governed_work_ref = None
        if config.governed_work_loop_enabled or os.environ.get("HG_GOVERNED_WORK_LOOP_ENABLED") == "1":
            from hg_runtime.governed_work_loop.work_envelope import load_work_envelope
            from hg_runtime.governed_work_loop.work_runner import run_governed_work_loop_once

            env = load_work_envelope(config.work_envelope_ref) if config.work_envelope_ref else None
            if not env:
                from hg_runtime.governed_work_loop.work_envelope import create_demo_envelope

                env, _ = create_demo_envelope(agent_id=config.agent_id, universe_ref=universe.universe_id)
            gw = run_governed_work_loop_once(env, config.session_id)
            governed_work_ref = gw.governed_work_receipt_id

            soak_id = os.environ.get("HG_REAL_SOAK_SOAK_ID")
            if soak_id and _live_posts_allowed(soak_id):
                from hg_runtime.real_soak_launch.live_dispatch_bridge import (
                    attempt_real_soak_live_moltbook_post,
                    get_live_posts_used,
                )
                from hg_runtime.real_soak_launch.moltbook_envelope import load_armed_envelope

                armed = load_armed_envelope(soak_id)
                if armed and get_live_posts_used(soak_id) < armed.max_live_posts and observed_turns >= 2:
                    live_result = attempt_real_soak_live_moltbook_post(
                        soak_id=soak_id,
                        stop_active=check_stop(config.session_id, base=store_base),
                        panic_active=check_panic(config.session_id, base=store_base),
                        context_summary=f"turn={observed_turns} task={gw.work_type}",
                        base=None,
                    )
                    if live_result.ok:
                        budget.external_side_effects += 1
                        budget._enforce()

        request = build_agent_turn_request(
            agent_id=config.agent_id,
            run_id=config.session_id,
            runtime_mode="local_dev",
            operator_presence="operator_absent",
            allow_live_read=config.allow_live_read,
            allow_provider=config.allow_provider,
        )
        outcome = _turn_executor(request, turn_base=tbase)

        if isinstance(outcome, AgentTurnFailure):
            budget.record_turn(
                verdict=outcome.verdict.value,
                has_receipt=False,
                broker_ref=None,
                external_side_effect=False,
            )
            final_verdict = HandsOffSessionVerdict.RED_TURN_WITHOUT_RECEIPT
            break

        turn_receipt_ref = outcome.turn_receipt_ref
        broker_ref = outcome.broker_decision_ref
        external_se = outcome.verdict == AgentTurnVerdict.RED_AGENT_TURN_EXTERNAL_SIDE_EFFECT

        if not turn_receipt_ref:
            budget.record_turn(verdict="RED_NO_RECEIPT", has_receipt=False, broker_ref=broker_ref, external_side_effect=external_se)
            final_verdict = HandsOffSessionVerdict.RED_TURN_WITHOUT_RECEIPT
            break

        if not ts_result.receipt:
            final_verdict = HandsOffSessionVerdict.RED_TASK_SELECTION_WITHOUT_RECEIPT
            break

        observed_turns += 1
        state.turn_count = observed_turns

        cont = ContinuousTurnReceipt(
            continuous_turn_receipt_id=f"cont-turn-{config.session_id}-{observed_turns}",
            session_id=config.session_id,
            turn_index=observed_turns,
            turn_receipt_ref=turn_receipt_ref,
            task_selection_receipt_ref=ts_result.receipt.task_selection_receipt_id,
            broker_decision_ref=broker_ref or ts_result.decision.broker_decision_ref,
            selected_task_type=ts_result.selected.task_type,
            verdict=outcome.verdict.value,
            external_side_effect=external_se,
            governed_work_receipt_ref=governed_work_ref,
            created_at=now_iso(),
        ).with_hash()
        persist_continuous_turn_receipt(cont, base=store_base)

        try:
            budget.record_turn(
                verdict=outcome.verdict.value,
                has_receipt=True,
                broker_ref=broker_ref or ts_result.decision.broker_decision_ref,
                external_side_effect=external_se,
            )
        except HandsOffBudgetError as exc:
            if "YELLOW" in str(exc):
                final_verdict = HandsOffSessionVerdict.YELLOW_RESOURCE_THROTTLED
            else:
                final_verdict = HandsOffSessionVerdict(exc.args[0]) if exc.args else HandsOffSessionVerdict.RED_BUDGET_EXCEEDED
            break

        if outcome.verdict == AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_PROVIDER_UNAVAILABLE:
            if final_verdict == HandsOffSessionVerdict.GREEN_SESSION_COMPLETE:
                final_verdict = HandsOffSessionVerdict.YELLOW_PROVIDER_UNAVAILABLE
        if outcome.verdict == AgentTurnVerdict.YELLOW_AGENT_TURN_DEFERRED_LIVE_READ_UNAVAILABLE:
            if final_verdict == HandsOffSessionVerdict.GREEN_SESSION_COMPLETE:
                final_verdict = HandsOffSessionVerdict.YELLOW_LIVE_READ_UNAVAILABLE

        if external_se:
            final_verdict = HandsOffSessionVerdict.RED_EXTERNAL_SIDE_EFFECT
            break

        hb = write_heartbeat(
            session_id=config.session_id,
            pid=pid,
            turn_count=observed_turns,
            status=HandsOffSessionStatus.RUNNING.value,
            base=store_base,
        )
        heartbeat_lock(config.session_id, base=store_base)

        state = HandsOffSessionState(
            session_id=config.session_id,
            pid=pid,
            status=HandsOffSessionStatus.RUNNING.value,
            started_at=started_at,
            turn_count=observed_turns,
            selected_task_count=state.selected_task_count,
            idle_count=state.idle_count,
            last_turn_ref=turn_receipt_ref,
            last_task_selection_ref=ts_result.receipt.task_selection_receipt_id,
            last_broker_decision_ref=broker_ref or ts_result.decision.broker_decision_ref,
            last_heartbeat_ref=hb.heartbeat_id,
            last_governed_work_receipt_ref=governed_work_ref,
            stop_requested=stop_requested,
            panic_requested=panic_requested,
            failure_budget_status="ok",
            resource_budget_status=budget.to_payload(),
        ).with_hash()
        persist_state(state, base=store_base)

        time.sleep(config.turn_interval_seconds)

    status = HandsOffSessionStatus.PANIC if panic_requested else HandsOffSessionStatus.STOPPED
    if str(final_verdict).startswith("RED_"):
        status = HandsOffSessionStatus.FAILED_CLOSED

    state = HandsOffSessionState(
        session_id=config.session_id,
        pid=pid,
        status=status.value,
        started_at=started_at,
        stopped_at=now_iso(),
        turn_count=state.turn_count,
        selected_task_count=state.selected_task_count,
        idle_count=state.idle_count,
        last_turn_ref=state.last_turn_ref,
        last_task_selection_ref=state.last_task_selection_ref,
        last_broker_decision_ref=state.last_broker_decision_ref,
        last_heartbeat_ref=state.last_heartbeat_ref,
        stop_requested=stop_requested,
        panic_requested=panic_requested,
        failure_budget_status=budget.to_payload(),
        resource_budget_status=budget.to_payload(),
        external_side_effect_count=budget.external_side_effects,
    ).with_hash()
    persist_state(state, base=store_base)
    release_lock(config.session_id, status=status.value, base=store_base)

    postflight = SessionPostflight(
        postflight_id=f"postflight-{config.session_id}",
        session_id=config.session_id,
        verdict=final_verdict.value if hasattr(final_verdict, "value") else str(final_verdict),
        turn_count=state.turn_count,
        selected_task_count=state.selected_task_count,
        idle_count=state.idle_count,
        stop_requested=stop_requested,
        panic_requested=panic_requested,
        external_side_effect_count=budget.external_side_effects,
        background_process_survives=False,
        created_at=now_iso(),
    ).with_hash()
    write_postflight(postflight, base=store_base)
    return postflight


__all__ = ["run_hands_off_session"]
