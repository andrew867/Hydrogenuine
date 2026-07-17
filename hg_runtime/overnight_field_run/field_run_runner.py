"""Overnight field run runner — Phase 22 + Phase 23 integration."""

from __future__ import annotations

import json
import os
from pathlib import Path

from hg_runtime.governed_work_loop.action_quota import reset_quota_for_run
from hg_runtime.governed_work_loop.work_envelope import create_demo_envelope
from hg_runtime.hands_off_session.manual_controls import check_panic, check_stop, ensure_controls_available
from hg_runtime.hands_off_session.schema import STORE_ROOT as HO_STORE
from hg_runtime.hands_off_session.session_config import HandsOffSessionConfig, validate_session_config
from hg_runtime.hands_off_session.session_receipts import list_continuous_turn_receipts
from hg_runtime.hands_off_session.session_runner import run_hands_off_session
from hg_runtime.hands_off_session.session_state import load_state as load_ho_state
from hg_runtime.overnight_field_run.continuity_audit import run_continuity_audit
from hg_runtime.overnight_field_run.errors import FieldRunConfigError, FieldRunLockError, OvernightFieldRunError
from hg_runtime.overnight_field_run.field_run_config import OvernightFieldRunConfig, validate_field_run_config
from hg_runtime.overnight_field_run.field_run_lock import acquire_field_run_lock, release_field_run_lock
from hg_runtime.overnight_field_run.field_run_postflight import FieldRunPostflight, load_postflight, resolve_verdict, write_postflight
from hg_runtime.overnight_field_run.field_run_receipts import (
    make_checkpoint_receipt,
    make_start_receipt,
    make_stop_receipt,
    persist_checkpoint_receipt,
    persist_start_receipt,
    persist_stop_receipt,
)
from hg_runtime.overnight_field_run.field_run_state import OvernightFieldRunState, load_state, persist_state
from hg_runtime.overnight_field_run.incident_summary import build_incident_summary
from hg_runtime.overnight_field_run.schema import FieldRunMode, FieldRunStatus, STORE_ROOT, field_run_dir, now_iso
from hg_runtime.overnight_field_run.wake_report import build_wake_report


def _hands_off_config(config: OvernightFieldRunConfig) -> HandsOffSessionConfig:
    envelope_ref = config.governed_work_envelope_ref
    if not envelope_ref:
        env, _ = create_demo_envelope(agent_id=config.agent_id, universe_ref=config.objective_universe_ref)
        envelope_ref = env.envelope_id

    ho = HandsOffSessionConfig(
        session_id=config.field_run_id,
        agent_id=config.agent_id,
        objective_universe_ref=config.objective_universe_ref,
        foreground_required=config.foreground_required,
        manual_stop_required=config.manual_stop_required,
        panic_required=config.panic_required,
        scheduler_allowed=config.scheduler_allowed,
        daemon_allowed=config.daemon_allowed,
        service_allowed=config.service_allowed,
        cron_allowed=config.cron_allowed,
        fixed_turn_cap=config.fixed_turn_cap,
        fixed_duration_cap=config.fixed_duration_cap,
        turn_interval_seconds=config.turn_interval_seconds,
        external_side_effects_allowed=config.external_side_effects_allowed,
        live_writes_allowed=config.live_writes_allowed,
        test_only_stop_after_observed_turns=config.test_only_stop_after_observed_turns,
        governed_work_loop_enabled=True,
        work_envelope_ref=envelope_ref,
        created_at=config.created_at,
    )
    production = config.mode == FieldRunMode.OPERATOR_FIELD_RUN.value and config.test_only_stop_after_observed_turns is None
    return validate_session_config(ho, production_mode=production)


def _write_checkpoints_from_turns(
    field_run_id: str,
    session_id: str,
    *,
    interval: int,
    ho_base: Path | None,
    field_base: Path | None,
) -> list[str]:
    refs: list[str] = []
    receipts = list_continuous_turn_receipts(session_id, base=ho_base)
    if not receipts:
        return refs
    for i, turn in enumerate(receipts, start=1):
        if i % max(interval, 1) != 0 and i != len(receipts):
            continue
        cp = make_checkpoint_receipt(
            field_run_id,
            turn_count=i,
            task_selection_count=i,
            governed_work_count=i,
            heartbeat_ref=f"hb-turn-{i}",
            external_side_effect_count=1 if turn.external_side_effect else 0,
        )
        persist_checkpoint_receipt(cp, base=field_base)
        refs.append(cp.checkpoint_receipt_id)
    return refs


def _sync_field_state(
    config: OvernightFieldRunConfig,
    *,
    ho_base: Path | None,
    field_base: Path | None,
    started_at: str,
    pid: int,
) -> OvernightFieldRunState:
    ho = load_ho_state(config.field_run_id, base=ho_base)
    receipts = list_continuous_turn_receipts(config.field_run_id, base=ho_base)
    task_types = [r.selected_task_type or "unknown" for r in receipts]
    refusals = [r.verdict for r in receipts if "REFUS" in r.verdict.upper() or "RED_" in r.verdict]

    checkpoint_refs = _write_checkpoints_from_turns(
        config.field_run_id,
        config.field_run_id,
        interval=config.checkpoint_interval_turns,
        ho_base=ho_base,
        field_base=field_base,
    )

    state = OvernightFieldRunState(
        field_run_id=config.field_run_id,
        pid=pid,
        mode=config.mode,
        status=ho.status if ho else FieldRunStatus.STOPPED.value,
        started_at=started_at,
        stopped_at=ho.stopped_at if ho else now_iso(),
        turn_count=ho.turn_count if ho else 0,
        task_selection_count=ho.selected_task_count if ho else 0,
        governed_work_count=sum(1 for r in receipts if r.governed_work_receipt_ref),
        internal_work_count=sum(1 for r in receipts if r.governed_work_receipt_ref),
        refusal_count=len(refusals),
        idle_count=ho.idle_count if ho else 0,
        checkpoint_count=len(checkpoint_refs),
        last_checkpoint_ref=checkpoint_refs[-1] if checkpoint_refs else "",
        last_selected_task_type=task_types[-1] if task_types else "",
        last_turn_receipt_ref=ho.last_turn_ref if ho else "",
        last_task_selection_ref=ho.last_task_selection_ref if ho else "",
        last_governed_work_ref=ho.last_governed_work_receipt_ref if ho else "",
        last_heartbeat_ref=ho.last_heartbeat_ref if ho else "",
        stop_requested=ho.stop_requested if ho else False,
        panic_requested=ho.panic_requested if ho else False,
        external_side_effect_count=ho.external_side_effect_count if ho else 0,
        hands_off_session_id=config.field_run_id,
    ).with_hash()
    persist_state(state, base=field_base)
    return state


def run_overnight_field_session(
    config: OvernightFieldRunConfig,
    *,
    base: Path | None = None,
    ho_base: Path | None = None,
    turn_base: Path | None = None,
) -> FieldRunPostflight:
    """Run foreground overnight field session until STOP/PANIC/failure."""
    field_base = base or STORE_ROOT
    hands_off_base = ho_base or HO_STORE

    if config.mode == FieldRunMode.POSTFLIGHT_ONLY.value:
        existing = load_postflight(config.field_run_id, base=field_base)
        if existing:
            return existing
        raise OvernightFieldRunError("RED_POSTFLIGHT_MISSING")

    production = config.mode == FieldRunMode.OPERATOR_FIELD_RUN.value and config.test_only_stop_after_observed_turns is None
    config = validate_field_run_config(config, production_mode=production)

    run_dir = field_run_dir(config.field_run_id, base=field_base)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.json").write_text(json.dumps(config.to_payload(), indent=2) + "\n", encoding="utf-8")

    try:
        acquire_field_run_lock(config.field_run_id, base=field_base)
    except FieldRunLockError as exc:
        raise OvernightFieldRunError(str(exc)) from exc

    pid = os.getpid()
    started_at = now_iso()
    reset_quota_for_run(config.field_run_id)

    try:
        start = make_start_receipt(config.field_run_id, config.hash or "", config.mode, pid)
        persist_start_receipt(start, base=field_base)
        ensure_controls_available(config.field_run_id, base=hands_off_base)

        initial = OvernightFieldRunState(
            field_run_id=config.field_run_id,
            pid=pid,
            mode=config.mode,
            status=FieldRunStatus.STARTING.value,
            started_at=started_at,
            hands_off_session_id=config.field_run_id,
        ).with_hash()
        persist_state(initial, base=field_base)

        ho_config = _hands_off_config(config)
        session_postflight = run_hands_off_session(
            ho_config,
            base=hands_off_base,
            turn_base=turn_base,
            production_mode=production,
        )
    except Exception:
        release_field_run_lock(config.field_run_id, base=field_base)
        raise

    state = _sync_field_state(config, ho_base=hands_off_base, field_base=field_base, started_at=started_at, pid=pid)
    stopped_at = state.stopped_at or now_iso()

    stop_reason = "panic" if state.panic_requested else ("stop" if state.stop_requested else "session_complete")
    stop = make_stop_receipt(
        config.field_run_id,
        stop_reason=stop_reason,
        turn_count=state.turn_count,
        panic_requested=state.panic_requested,
        stop_requested=state.stop_requested,
    )
    persist_stop_receipt(stop, base=field_base)

    continuity = run_continuity_audit(
        config.field_run_id,
        state_payload=state.to_payload(),
        session_id=config.field_run_id,
        hands_off_base=hands_off_base,
        field_base=field_base,
    )

    incidents: list[str] = []
    if state.panic_requested:
        incidents.append("operator_panic")
    if state.external_side_effect_count > 0:
        incidents.append("external_side_effect")

    build_incident_summary(
        config.field_run_id,
        incidents=incidents,
        panic_requested=state.panic_requested,
        stop_requested=state.stop_requested,
        session_verdict=session_postflight.verdict,
        base=field_base,
    )

    from datetime import datetime, timezone

    try:
        start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        stop_dt = datetime.fromisoformat(stopped_at.replace("Z", "+00:00"))
        elapsed = max((stop_dt - start_dt).total_seconds(), 0.0)
    except (ValueError, TypeError):
        elapsed = 0.0
    receipts = list_continuous_turn_receipts(config.field_run_id, base=hands_off_base)
    task_types = [r.selected_task_type or "unknown" for r in receipts]
    refusals = [r.verdict for r in receipts if "REFUS" in r.verdict.upper()]

    verdict = resolve_verdict(
        mode=config.mode,
        session_verdict=session_postflight.verdict,
        turn_count=state.turn_count,
        external_side_effects=state.external_side_effect_count,
        continuity_verdict=continuity.verdict,
        elapsed_seconds=elapsed,
    )

    wake = build_wake_report(
        config.field_run_id,
        mode=config.mode,
        started_at=started_at,
        stopped_at=stopped_at,
        elapsed_seconds=elapsed,
        state_payload=state.to_payload(),
        stop_reason=stop_reason,
        task_types=task_types,
        refusals=refusals,
        incidents=incidents,
        receipt_hashes=[start.hash or "", stop.hash or ""],
        continuity_verdict=continuity.verdict,
        postflight_verdict=verdict,
        base=field_base,
    )

    infrastructure_only = config.mode == FieldRunMode.INFRASTRUCTURE_SMOKE.value
    postflight = FieldRunPostflight(
        postflight_id=f"postflight-{config.field_run_id}",
        field_run_id=config.field_run_id,
        mode=config.mode,
        verdict=verdict,
        turn_count=state.turn_count,
        task_selection_count=state.task_selection_count,
        governed_work_count=state.governed_work_count,
        external_side_effect_count=state.external_side_effect_count,
        background_process_survives=False,
        wake_report_ref=wake.wake_report_id,
        continuity_audit_ref=continuity.continuity_audit_id,
        stop_requested=state.stop_requested,
        panic_requested=state.panic_requested,
        infrastructure_only=infrastructure_only,
        created_at=now_iso(),
    ).with_hash()
    write_postflight(postflight, base=field_base)
    release_field_run_lock(config.field_run_id, base=field_base)
    return postflight


__all__ = ["run_overnight_field_session"]
