"""ELS wake lifecycle state machine and orchestration."""

from __future__ import annotations

import os
from typing import Any

from hg_runtime.contract import stable_id
from hg_runtime.emergence.config import ELSConfig
from hg_runtime.emergence import rtc_bridge as bridge
from hg_runtime.emergence.posture import select_posture
from hg_runtime.emergence.profiles import get_profile
from hg_runtime.emergence.readiness import ReadinessContext, aggregate_verdict, run_all_checks
from hg_runtime.emergence.types import WakeRequest, WakeResult
from hg_runtime.replay import replay
from hg_runtime import world_state as ws

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "COLD": frozenset({"WAKE_REQUESTED"}),
    "WAKE_REQUESTED": frozenset({"PROCESS_STARTED", "WAKE_REFUSED"}),
    "PROCESS_STARTED": frozenset({"CONFIG_LOADED", "WAKE_FAILED"}),
    "CONFIG_LOADED": frozenset({"IDENTITY_BOUND", "WAKE_REFUSED"}),
    "IDENTITY_BOUND": frozenset({"EVENT_BUS_CONNECTED", "WAKE_REFUSED"}),
    "EVENT_BUS_CONNECTED": frozenset({"EVENT_HEAD_READ", "WAKE_REFUSED"}),
    "EVENT_HEAD_READ": frozenset({"REPLAY_VERIFIED", "REPLAY_FAILED", "WAKE_REFUSED"}),
    "REPLAY_VERIFIED": frozenset({"WORLD_STATE_DERIVED", "SAFE_MODE_ENTERED"}),
    "REPLAY_FAILED": frozenset({"SAFE_MODE_ENTERED", "WAKE_REFUSED"}),
    "WORLD_STATE_DERIVED": frozenset({"MEMORY_CONTEXT_LOADED", "WAKE_REFUSED"}),
    "MEMORY_CONTEXT_LOADED": frozenset({"POSTURE_SELECTED", "WAKE_REFUSED"}),
    "POSTURE_SELECTED": frozenset({"CAPABILITY_CATALOG_LOADED", "WAKE_REFUSED"}),
    "CAPABILITY_CATALOG_LOADED": frozenset({"QUIET_SETTLING_OPTIONAL", "READY_DECLARED", "DEGRADED_READY_DECLARED", "WAKE_REFUSED"}),
    "QUIET_SETTLING_OPTIONAL": frozenset({"READY_DECLARED", "DEGRADED_READY_DECLARED", "WAKE_REFUSED"}),
    "READY_DECLARED": frozenset({"WORK_ADMISSION_OPEN"}),
    "DEGRADED_READY_DECLARED": frozenset({"WORK_ADMISSION_OPEN"}),
    "SAFE_MODE_ENTERED": frozenset(),
    "WAKE_REFUSED": frozenset(),
    "WAKE_FAILED": frozenset(),
    "WORK_ADMISSION_OPEN": frozenset(),
}

FORBIDDEN_TRANSITIONS: tuple[tuple[str, str], ...] = (
    ("COLD", "READY_DECLARED"),
    ("PROCESS_STARTED", "WORK_ADMISSION_OPEN"),
    ("IDENTITY_BOUND", "WORK_ADMISSION_OPEN"),
    ("EVENT_BUS_CONNECTED", "READY_DECLARED"),
    ("WAKE_FAILED", "WORK_ADMISSION_OPEN"),
    ("WAKE_REFUSED", "WORK_ADMISSION_OPEN"),
)


def can_transition(from_state: str, to_state: str) -> bool:
    if (from_state, to_state) in FORBIDDEN_TRANSITIONS:
        return False
    allowed = ALLOWED_TRANSITIONS.get(from_state, frozenset())
    return to_state in allowed


def _bus_head_seq(bus: Any) -> int | None:
    if bus is None:
        return None
    if hasattr(bus, "next_seq"):
        return max(0, int(bus.next_seq) - 1)
    return None


def _build_context(
    *,
    config: ELSConfig,
    request: WakeRequest,
    bus: Any,
    runtime_dir: Any,
    clock_now: str,
    panic_active: bool = False,
    lockdown_active: bool = False,
    memory_available: bool = True,
    stale_scratch: bool = False,
    crr_recovery_marker: bool = False,
    crr_snapshot_hash: str | None = None,
    expected_world_state_hash: str | None = None,
    replay_force_fail: bool = False,
    scope: tuple[str, ...] | None = None,
) -> ReadinessContext:
    return ReadinessContext(
        runtime_dir=runtime_dir,
        bus=bus,
        agent_id=request.agent_id,
        operator_id=request.operator_id or config.operator_id,
        scope=scope if scope is not None else request.scope,
        panic_active=panic_active,
        lockdown_active=lockdown_active,
        memory_available=memory_available,
        oea_real=os.environ.get("HG_OEA_REAL", "0") == "1",
        oea_available=os.environ.get("HG_OEA_REAL", "0") != "1" or os.environ.get("HG_OEA_AVAILABLE", "0") == "1",
        live_cognition=os.environ.get("HG_RTC_COGNITION_LIVE", "0") == "1",
        live_provider_ok=os.environ.get("HG_RTC_COGNITION_LIVE", "0") == "1" and bool(
            os.environ.get("HG_COGNITION_PROVIDER_URL")
        ),
        secrets_redaction=True,
        stale_scratch=stale_scratch,
        crr_recovery_marker=crr_recovery_marker,
        crr_snapshot_hash=crr_snapshot_hash,
        expected_world_state_hash=expected_world_state_hash,
        replay_force_fail=replay_force_fail,
        clock_now=clock_now,
    )


def run_wake_cycle(
    *,
    config: ELSConfig,
    request: WakeRequest,
    bus: Any,
    runtime_dir: Any,
    clock_now: str,
    panic_active: bool = False,
    lockdown_active: bool = False,
    memory_available: bool = True,
    stale_scratch: bool = False,
    crr_recovery_marker: bool = False,
    crr_snapshot_hash: str | None = None,
    expected_world_state_hash: str | None = None,
    replay_force_fail: bool = False,
    ysr_drafts: list[dict[str, Any]] | None = None,
    msc_drafts: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], WakeResult]:
    """Run full wake lifecycle; return event drafts and result. No bus writes."""
    wake_id = stable_id("els_wake", request.agent_id, request.profile, clock_now)
    profile = get_profile(request.profile)
    ctx = _build_context(
        config=config,
        request=request,
        bus=bus,
        runtime_dir=runtime_dir,
        clock_now=clock_now,
        panic_active=panic_active,
        lockdown_active=lockdown_active,
        memory_available=memory_available,
        stale_scratch=stale_scratch,
        crr_recovery_marker=crr_recovery_marker,
        crr_snapshot_hash=crr_snapshot_hash,
        expected_world_state_hash=expected_world_state_hash,
        replay_force_fail=replay_force_fail,
    )

    drafts: list[dict[str, Any]] = []
    states: list[str] = ["COLD"]
    current = "COLD"

    def advance(to_state: str) -> bool:
        nonlocal current
        if not can_transition(current, to_state):
            return False
        current = to_state
        states.append(to_state)
        return True

    advance("WAKE_REQUESTED")
    drafts.append(bridge.wake_requested(wake_id, request))

    if not config.enabled:
        advance("WAKE_REFUSED")
        result = WakeResult(
            wake_id=wake_id,
            agent_id=request.agent_id,
            profile=request.profile,
            final_state="WAKE_REFUSED",
            posture="OFFLINE_REPLAY_ONLY",
            verdict="refused",
            work_admission_open=False,
            checks=[],
            states_visited=states,
            refusal_reason="els_disabled",
        )
        drafts.append(bridge.wake_refused(wake_id, request, reason="els_disabled"))
        return drafts, result

    advance("PROCESS_STARTED")
    drafts.append(bridge.process_started(wake_id, request))

    advance("CONFIG_LOADED")
    drafts.append(bridge.config_loaded(wake_id, request))

    if not ctx.agent_id and profile.required_checks and "identity_bound" in profile.required_checks:
        advance("WAKE_REFUSED")
        result = WakeResult(
            wake_id=wake_id,
            agent_id=request.agent_id or "",
            profile=request.profile,
            final_state="WAKE_REFUSED",
            posture="OFFLINE_REPLAY_ONLY",
            verdict="refused",
            work_admission_open=False,
            states_visited=states,
            refusal_reason="IDENTITY_MISSING",
        )
        drafts.append(bridge.wake_refused(wake_id, request, reason="IDENTITY_MISSING"))
        return drafts, result

    advance("IDENTITY_BOUND")
    drafts.append(bridge.identity_bound(wake_id, request))

    if ctx.bus is None:
        advance("WAKE_REFUSED")
        result = WakeResult(
            wake_id=wake_id,
            agent_id=request.agent_id,
            profile=request.profile,
            final_state="WAKE_REFUSED",
            posture="OFFLINE_REPLAY_ONLY",
            verdict="refused",
            work_admission_open=False,
            states_visited=states,
            refusal_reason="EVENT_BUS_MISSING",
        )
        drafts.append(bridge.wake_refused(wake_id, request, reason="EVENT_BUS_MISSING"))
        return drafts, result

    advance("EVENT_BUS_CONNECTED")
    drafts.append(bridge.event_bus_connected(wake_id, request))

    head = _bus_head_seq(bus)
    advance("EVENT_HEAD_READ")
    drafts.append(bridge.event_head_read(wake_id, request, event_head_seq=head))

    if config.ysr_on_stale_scratch and stale_scratch and ysr_drafts:
        drafts.extend(ysr_drafts)

    replay_result = replay(runtime_dir) if not replay_force_fail else None
    replay_ok = replay_result.ok if replay_result else False

    if replay_force_fail or (replay_result and not replay_ok):
        advance("REPLAY_FAILED")
        drafts.append(bridge.replay_failed(wake_id, request, reason="REPLAY_MISMATCH"))
        if config.refuse_on_replay_mismatch:
            advance("SAFE_MODE_ENTERED")
            drafts.append(bridge.safe_mode_entered(wake_id, request, reason="REPLAY_MISMATCH"))
            checks = run_all_checks(profile, ctx)
            for check in checks:
                drafts.append(bridge.readiness_check_recorded(wake_id, check))
            posture = select_posture(profile=profile, checks=checks, verdict="safe_mode", ctx=ctx)
            advance("WAKE_REFUSED")
            drafts.append(bridge.wake_refused(wake_id, request, reason="REPLAY_MISMATCH"))
            result = WakeResult(
                wake_id=wake_id,
                agent_id=request.agent_id,
                profile=request.profile,
                final_state="WAKE_REFUSED",
                posture=posture,
                verdict="safe_mode",
                work_admission_open=False,
                checks=checks,
                states_visited=states,
                event_head_seq=head,
                refusal_reason="REPLAY_MISMATCH",
            )
            return drafts, result
    else:
        advance("REPLAY_VERIFIED")
        drafts.append(bridge.replay_verified(wake_id, request, replay_hash=replay_result.state_hash if replay_result else None))

    advance("WORLD_STATE_DERIVED")
    state_hash = replay_result.state_hash if replay_result else ws.state_hash(ws.initial_state())
    drafts.append(bridge.world_state_derived(wake_id, request, state_hash=state_hash))

    checks = run_all_checks(profile, ctx)
    for check in checks:
        drafts.append(bridge.readiness_check_recorded(wake_id, check))

    advance("MEMORY_CONTEXT_LOADED")
    mem_status = next((c.status for c in checks if c.check_id == "memory_context_loaded_or_degraded"), "pass")
    drafts.append(bridge.memory_context_loaded(wake_id, request, status=mem_status))

    verdict, refusal_reason = aggregate_verdict(
        checks,
        profile=profile,
        panic_active=panic_active,
        lockdown_active=lockdown_active,
        replay_failed=replay_force_fail or not replay_ok,
        refuse_on_replay_mismatch=config.refuse_on_replay_mismatch,
    )
    posture = select_posture(profile=profile, checks=checks, verdict=verdict, ctx=ctx)

    advance("POSTURE_SELECTED")
    drafts.append(bridge.posture_selected(wake_id, request, posture=posture))

    advance("CAPABILITY_CATALOG_LOADED")
    drafts.append(bridge.capability_catalog_loaded(wake_id, request))

    if config.allow_quiet_settling and profile.allow_quiet_settling and msc_drafts:
        advance("QUIET_SETTLING_OPTIONAL")
        drafts.append(bridge.quiet_settling_started(wake_id, request))
        drafts.extend(msc_drafts)
        drafts.append(bridge.quiet_settling_completed(wake_id, request))

    if verdict in ("refused", "failed", "safe_mode") and refusal_reason:
        if verdict == "safe_mode":
            advance("SAFE_MODE_ENTERED")
            drafts.append(bridge.safe_mode_entered(wake_id, request, reason=refusal_reason))
        advance("WAKE_REFUSED")
        drafts.append(bridge.wake_refused(wake_id, request, reason=refusal_reason))
        result = WakeResult(
            wake_id=wake_id,
            agent_id=request.agent_id,
            profile=request.profile,
            final_state="WAKE_REFUSED",
            posture=posture,
            verdict=verdict,  # type: ignore[arg-type]
            work_admission_open=False,
            checks=checks,
            states_visited=states,
            event_head_seq=head,
            world_state_hash=state_hash,
            refusal_reason=refusal_reason,
        )
        return drafts, result

    if verdict == "degraded_ready":
        advance("DEGRADED_READY_DECLARED")
        drafts.append(bridge.degraded_ready_declared(wake_id, request, posture=posture))
    else:
        advance("READY_DECLARED")
        drafts.append(bridge.ready_declared(wake_id, request, posture=posture))

    advance("WORK_ADMISSION_OPEN")
    drafts.append(bridge.work_admission_opened(wake_id, request, posture=posture))

    result = WakeResult(
        wake_id=wake_id,
        agent_id=request.agent_id,
        profile=request.profile,
        final_state="WORK_ADMISSION_OPEN",
        posture=posture,
        verdict=verdict,  # type: ignore[arg-type]
        work_admission_open=True,
        checks=checks,
        states_visited=states,
        event_head_seq=head,
        world_state_hash=state_hash,
        authority_freshened=False,
    )
    return drafts, result


__all__ = [
    "ALLOWED_TRANSITIONS",
    "FORBIDDEN_TRANSITIONS",
    "can_transition",
    "run_wake_cycle",
]
