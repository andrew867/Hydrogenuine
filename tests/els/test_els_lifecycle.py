"""ELS emergence lifecycle tests."""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from hg_dep.appliance_config import ApplianceConfig
from hg_dep.appliance_runtime import ApplianceRuntime
from hg_plt.service import AgentZeroService
from hg_runtime import world_state as ws
from hg_runtime.bus import EventBus
from hg_runtime.emergence.config import ELSConfig
from hg_runtime.emergence.handler import Phase1ELSHandler, StubELSHandler
from hg_runtime.emergence.lifecycle import FORBIDDEN_TRANSITIONS, can_transition, run_wake_cycle
from hg_runtime.emergence.posture import select_posture
from hg_runtime.emergence.readiness import ReadinessContext, aggregate_verdict, run_all_checks
from hg_runtime.emergence.profiles import get_profile
from hg_runtime.emergence.subagents import run_subagent_wake
from hg_runtime.emergence.types import SubAgentDeclaration, WakeRequest
from hg_runtime.replay import replay
from tests.els.conftest import emit_drafts, _clock

ELS_TYPES = {
    "ELS_WAKE_REQUESTED",
    "ELS_PROCESS_STARTED",
    "ELS_CONFIG_LOADED",
    "ELS_IDENTITY_BOUND",
    "ELS_EVENT_BUS_CONNECTED",
    "ELS_EVENT_HEAD_READ",
    "ELS_REPLAY_VERIFIED",
    "ELS_REPLAY_FAILED",
    "ELS_WORLD_STATE_DERIVED",
    "ELS_MEMORY_CONTEXT_LOADED",
    "ELS_READINESS_CHECK_RECORDED",
    "ELS_POSTURE_SELECTED",
    "ELS_CAPABILITY_CATALOG_LOADED",
    "ELS_QUIET_SETTLING_STARTED",
    "ELS_QUIET_SETTLING_COMPLETED",
    "ELS_READY_DECLARED",
    "ELS_DEGRADED_READY_DECLARED",
    "ELS_WORK_ADMISSION_OPENED",
    "ELS_WAKE_REFUSED",
    "ELS_WAKE_FAILED",
    "ELS_SAFE_MODE_ENTERED",
    "ELS_SUBAGENT_DECLARED",
    "ELS_SUBAGENT_IDENTITY_BOUND",
    "ELS_SUBAGENT_SCOPE_BOUND",
    "ELS_SUBAGENT_CONTEXT_LOADED",
    "ELS_SUBAGENT_READY",
    "ELS_SUBAGENT_REFUSED",
}

FORBIDDEN_AUTHORITY = {
    "DECISION_EVENT",
    "GPP_PERMIT_BOUND",
    "UEAK_EXECUTION_COMMITTED",
    "OEA_EXECUTION_COMPLETED",
    "TER_COMMAND_COMPLETED",
    "ACTION_COMMITTED",
    "SRP_APPLY_COMPLETED",
}


def _seed_bus(bus: EventBus, count: int = 3) -> None:
    for i in range(count):
        bus.submit("TIMER_EVENT", {"i": i}, source="timer")
    bus.poll(timeout=0.0)


def test_disabled_els_is_safe_noop(els_bus, els_runtime_dir):
    handler = StubELSHandler()
    assert handler.run_wake() == []
    assert handler.work_admission_open is True


def test_cold_wake_succeeds(els_config, els_runtime_dir, els_bus):
    _seed_bus(els_bus)
    request = WakeRequest(agent_id="agent0", profile="agent0_full", operator_id="op1")
    drafts, result = run_wake_cycle(
        config=els_config,
        request=request,
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:01.000000Z",
    )
    emit_drafts(els_bus, drafts)
    assert result.work_admission_open is True
    assert result.verdict == "ready"
    assert "READY_DECLARED" in result.states_visited
    assert "WORK_ADMISSION_OPEN" in result.states_visited
    types = [d["type"] for d in drafts]
    assert "ELS_READY_DECLARED" in types
    assert "ELS_WORK_ADMISSION_OPENED" in types
    assert not any(t in FORBIDDEN_AUTHORITY for t in types)


def test_missing_identity_refuses(els_config, els_runtime_dir, els_bus):
    request = WakeRequest(agent_id="", profile="agent0_full")
    drafts, result = run_wake_cycle(
        config=els_config,
        request=request,
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:02.000000Z",
    )
    assert result.work_admission_open is False
    assert result.verdict == "refused"
    assert any(d["type"] == "ELS_WAKE_REFUSED" for d in drafts)


def test_missing_event_bus_refuses(els_config, els_runtime_dir):
    request = WakeRequest(agent_id="agent0", profile="agent0_full")
    drafts, result = run_wake_cycle(
        config=els_config,
        request=request,
        bus=None,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:03.000000Z",
    )
    assert result.work_admission_open is False
    assert any(d["type"] == "ELS_WAKE_REFUSED" for d in drafts)
    assert result.refusal_reason == "EVENT_BUS_MISSING"


def test_replay_mismatch_safe_mode(els_config, els_runtime_dir, els_bus):
    _seed_bus(els_bus)
    request = WakeRequest(agent_id="agent0", profile="agent0_full")
    drafts, result = run_wake_cycle(
        config=els_config,
        request=request,
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:04.000000Z",
        replay_force_fail=True,
    )
    assert result.work_admission_open is False
    assert result.verdict == "safe_mode"
    assert any(d["type"] == "ELS_SAFE_MODE_ENTERED" for d in drafts)


def test_memory_unavailable_degrades_when_allowed(els_config, els_runtime_dir, els_bus):
    _seed_bus(els_bus)
    cfg = ELSConfig(**{**els_config.__dict__, "allow_degraded_memory": True})
    request = WakeRequest(agent_id="agent0", profile="agent0_full")
    drafts, result = run_wake_cycle(
        config=cfg,
        request=request,
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:05.000000Z",
        memory_available=False,
    )
    assert result.verdict == "degraded_ready"
    assert result.work_admission_open is True
    assert any(d["type"] == "ELS_DEGRADED_READY_DECLARED" for d in drafts)


def test_live_cognition_refuses_without_provider(els_config, els_runtime_dir, els_bus, monkeypatch):
    monkeypatch.setenv("HG_RTC_COGNITION_LIVE", "1")
    monkeypatch.delenv("HG_COGNITION_PROVIDER_URL", raising=False)
    request = WakeRequest(agent_id="worker-live", profile="live_cognition_worker", scope=("observe",))
    decl = SubAgentDeclaration(agent_id="worker-live", parent_agent_id="agent0", scope=("observe",))
    drafts, readiness = run_subagent_wake(
        config=els_config,
        declaration=decl,
        profile_id="live_cognition_worker",
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:06.000000Z",
    )
    assert readiness.ready is False
    assert any(d["type"] == "ELS_SUBAGENT_REFUSED" for d in drafts)


def test_oea_real_unavailable_degraded_not_fake_ready(els_runtime_dir, els_bus, monkeypatch):
    monkeypatch.setenv("HG_OEA_REAL", "1")
    monkeypatch.setenv("HG_OEA_AVAILABLE", "0")
    profile = get_profile("agent0_full")
    ctx = ReadinessContext(
        runtime_dir=els_runtime_dir,
        bus=els_bus,
        agent_id="agent0",
        operator_id=None,
        scope=(),
        panic_active=False,
        lockdown_active=False,
        memory_available=True,
        oea_real=True,
        oea_available=False,
        live_cognition=False,
        live_provider_ok=False,
        secrets_redaction=True,
        stale_scratch=False,
        crr_recovery_marker=False,
        crr_snapshot_hash=None,
        expected_world_state_hash=None,
        clock_now="2026-06-12T14:00:07.000000Z",
    )
    checks = run_all_checks(profile, ctx)
    oea_check = next(c for c in checks if c.check_id == "oea_mode_known")
    assert oea_check.status == "degraded"


def test_subagent_without_scope_refuses(els_config, els_runtime_dir, els_bus):
    decl = SubAgentDeclaration(agent_id="worker1", parent_agent_id="agent0", scope=())
    drafts, readiness = run_subagent_wake(
        config=els_config,
        declaration=decl,
        profile_id="task_subagent",
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:08.000000Z",
    )
    assert readiness.ready is False
    assert readiness.refusal_reason == "SCOPE_MISSING"


def test_subagent_with_scope_ready(els_config, els_runtime_dir, els_bus):
    _seed_bus(els_bus)
    decl = SubAgentDeclaration(agent_id="worker1", parent_agent_id="agent0", scope=("observe",))
    drafts, readiness = run_subagent_wake(
        config=els_config,
        declaration=decl,
        profile_id="task_subagent",
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:09.000000Z",
    )
    assert readiness.ready is True
    assert any(d["type"] == "ELS_SUBAGENT_READY" for d in drafts)


def test_work_admission_not_before_ready(els_config, els_runtime_dir, els_bus):
    _seed_bus(els_bus)
    request = WakeRequest(agent_id="agent0", profile="agent0_full")
    drafts, result = run_wake_cycle(
        config=els_config,
        request=request,
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:10.000000Z",
    )
    ready_idx = next(i for i, d in enumerate(drafts) if d["type"] == "ELS_READY_DECLARED")
    admission_idx = next(i for i, d in enumerate(drafts) if d["type"] == "ELS_WORK_ADMISSION_OPENED")
    assert admission_idx > ready_idx


@pytest.mark.parametrize("from_state,to_state", FORBIDDEN_TRANSITIONS)
def test_illegal_transitions_fail(from_state, to_state):
    assert can_transition(from_state, to_state) is False


def test_posture_deterministic(els_runtime_dir, els_bus):
    profile = get_profile("agent0_full")
    ctx = ReadinessContext(
        runtime_dir=els_runtime_dir,
        bus=els_bus,
        agent_id="agent0",
        operator_id=None,
        scope=(),
        panic_active=False,
        lockdown_active=False,
        memory_available=True,
        oea_real=False,
        oea_available=True,
        live_cognition=False,
        live_provider_ok=False,
        secrets_redaction=True,
        stale_scratch=False,
        crr_recovery_marker=False,
        crr_snapshot_hash=None,
        expected_world_state_hash=None,
        clock_now="2026-06-12T14:00:11.000000Z",
    )
    checks = run_all_checks(profile, ctx)
    p1 = select_posture(profile=profile, checks=checks, verdict="ready", ctx=ctx)
    p2 = select_posture(profile=profile, checks=checks, verdict="ready", ctx=ctx)
    assert p1 == p2 == "NORMAL"


def test_authority_not_freshened(els_config, els_runtime_dir, els_bus):
    _seed_bus(els_bus)
    request = WakeRequest(agent_id="agent0", profile="agent0_full")
    _, result = run_wake_cycle(
        config=els_config,
        request=request,
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:12.000000Z",
    )
    assert result.authority_freshened is False


def test_panic_forces_safe_mode(els_config, els_runtime_dir, els_bus):
    _seed_bus(els_bus)
    request = WakeRequest(agent_id="agent0", profile="agent0_full")
    drafts, result = run_wake_cycle(
        config=els_config,
        request=request,
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:13.000000Z",
        panic_active=True,
    )
    assert result.work_admission_open is False
    assert result.posture == "SAFE_MODE"


def test_lockdown_blocks_admission(els_config, els_runtime_dir, els_bus):
    _seed_bus(els_bus)
    request = WakeRequest(agent_id="agent0", profile="agent0_full")
    _, result = run_wake_cycle(
        config=els_config,
        request=request,
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:14.000000Z",
        lockdown_active=True,
    )
    assert result.work_admission_open is False


def test_crr_reentry_verifies_snapshot(els_config, els_runtime_dir, els_bus):
    _seed_bus(els_bus)
    request = WakeRequest(agent_id="agent0", profile="crr_reentry")
    _, result = run_wake_cycle(
        config=els_config,
        request=request,
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:15.000000Z",
        crr_recovery_marker=True,
        crr_snapshot_hash=None,
    )
    assert result.work_admission_open is False


def test_crr_reentry_succeeds_with_snapshot(els_config, els_runtime_dir, els_bus):
    _seed_bus(els_bus)
    request = WakeRequest(agent_id="agent0", profile="crr_reentry")
    _, result = run_wake_cycle(
        config=els_config,
        request=request,
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:16.000000Z",
        crr_recovery_marker=True,
        crr_snapshot_hash="sha256:abc",
    )
    assert result.work_admission_open is True


def test_replay_deterministic_with_els_events(els_config, els_runtime_dir, els_bus):
    _seed_bus(els_bus)
    request = WakeRequest(agent_id="agent0", profile="agent0_full")
    drafts, _ = run_wake_cycle(
        config=els_config,
        request=request,
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:17.000000Z",
    )
    emit_drafts(els_bus, drafts)
    assert replay(els_runtime_dir).ok is True
    state = replay(els_runtime_dir).state
    assert state["self"]["work_admission_open"] is True


def test_no_bus_emit_in_emergence_module():
    root = Path(__file__).resolve().parents[2] / "hg_runtime" / "emergence"
    offenders = []
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "emit":
                    offenders.append(path.name)
    assert offenders == []


def test_msc_drafts_do_not_grant_authority(els_config, els_runtime_dir, els_bus):
    _seed_bus(els_bus)
    msc_stub = [
        {
            "type": "MSC_SETTLED",
            "payload": {"observation_only": True, "summary": "quiet"},
            "causal_parents": [],
            "severity": None,
        }
    ]
    cfg = ELSConfig(**{**els_config.__dict__, "allow_quiet_settling": True, "msc_on_wake": True})
    request = WakeRequest(agent_id="agent0", profile="agent0_full")
    drafts, result = run_wake_cycle(
        config=cfg,
        request=request,
        bus=els_bus,
        runtime_dir=els_runtime_dir,
        clock_now="2026-06-12T14:00:18.000000Z",
        msc_drafts=msc_stub,
    )
    assert result.work_admission_open is True
    assert not any(d["type"] in FORBIDDEN_AUTHORITY for d in drafts)


def test_handler_integration(els_handler, els_bus, els_runtime_dir):
    els_handler.bind_runtime(els_bus, ws.initial_state())
    _seed_bus(els_bus)
    drafts = els_handler.run_wake()
    emit_drafts(els_bus, drafts)
    assert els_handler.work_admission_open is True
    report = els_handler.last_report
    assert report is not None
    assert report["ready_honest"] is True


def test_dep_consumes_els_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HG_ELS_ENABLED", "1")
    monkeypatch.setenv("HG_ELS_AGENT_ID", "agent0")
    config = ApplianceConfig(
        runtime_dir=tmp_path / "runtime",
        log_dir=tmp_path / "logs",
        cognition_mode="stub",
        max_ticks=1,
        require_enabled=False,
    )
    runtime = ApplianceRuntime(config)
    summary = runtime.start_bounded(max_ticks=1, submit_chat=True)
    assert summary["ok"] is True
    status = runtime.status()
    assert status.get("els_readiness") is not None or status.get("work_admission_open") is not None


def test_plt_displays_readiness_honestly(tmp_path, monkeypatch):
    workspace = Path(__file__).resolve().parents[2]
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    bus = EventBus(runtime_dir, clock=_clock())
    _seed_bus(bus)
    cfg = ELSConfig(enabled=True, agent_id="agent0", profile="agent0_full")
    request = WakeRequest(agent_id="agent0", profile="agent0_full")
    drafts, _ = run_wake_cycle(
        config=cfg,
        request=request,
        bus=bus,
        runtime_dir=runtime_dir,
        clock_now="2026-06-12T14:00:19.000000Z",
    )
    emit_drafts(bus, drafts)
    monkeypatch.setenv("HG_PLT_RUNTIME_DIR", str(runtime_dir))
    svc = AgentZeroService(workspace)
    emergence = svc.emergence()
    assert emergence["work_admission_open"] is True
    assert emergence["ready_honest"] is True
    assert emergence["wake_state"] == "WORK_ADMISSION_OPEN"
