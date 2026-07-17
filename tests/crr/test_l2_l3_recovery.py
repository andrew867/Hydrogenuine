"""CRR L2/L3 recovery integration tests."""

from __future__ import annotations

import os
import re
from pathlib import Path
from unittest import mock

import pytest

from hg_crr import (
    EligibilityState,
    L2L3CycleContext,
    L2L3RecoveryOrchestrator,
    Phase1RecoveryHandler,
    RecoveryEligibilityPolicy,
    delegate_l2_hygiene_cycle,
    delegate_l3_hygiene_cycle,
)
from hg_crr.checkpoint_manager import CheckpointManager
from hg_crr.eligibility import EligibilityResult
from hg_crr.executor_adapter import L2_HYGIENE_ACTIONS, L3_HYGIENE_ACTIONS, run_hygiene_action
from hg_crr.rehydrate import RehydrationVerifier
from hg_crr.types import TriggerDecision
from hg_runtime.bus import EventBus
from hg_runtime.handlers import (
    StubArousalReader,
    StubCognitionHandler,
    StubDecisionHandler,
    StubKernelHandler,
    StubMemoryHandler,
)
from hg_runtime.loop import RuntimeLoop
from hg_runtime.replay import replay


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T03:00:{counter['value']:02d}.000000Z"

    return tick


def _loop(tmp_path: Path, recovery: Phase1RecoveryHandler) -> RuntimeLoop:
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    return RuntimeLoop(
        bus,
        cognition=StubCognitionHandler(),
        decision=StubDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=StubArousalReader(),
        recovery=recovery,
        runtime_dir=tmp_path / "runtime",
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )


FORBIDDEN_HYGIENE_TOKENS = re.compile(
    r"\b(flush|compact|gc|prune|evict|archive|compact_session)\s*\(",
    re.IGNORECASE,
)


def test_l2_recovery_invokes_only_registered_adapters(tmp_path: Path):
    results = delegate_l2_hygiene_cycle(cycle_id="c2", context={"workspace_root": str(tmp_path)})
    assert len(results) == len(L2_HYGIENE_ACTIONS)
    for result, _event_type in results:
        assert result.executor_ref.startswith("hg_core.") or result.status == "failed"
        assert result.status in {"skipped_not_invoked", "completed", "failed", "unavailable"}


def test_l3_recovery_invokes_only_registered_adapters(tmp_path: Path):
    results = delegate_l3_hygiene_cycle(cycle_id="c3", context={"workspace_root": str(tmp_path)})
    assert len(results) == len(L3_HYGIENE_ACTIONS)
    for result, _event_type in results:
        assert result.status != "delegated_not_invoked"
        assert result.status in {"skipped_not_invoked", "completed", "failed", "unavailable"}


def test_missing_executor_does_not_report_fake_success():
    result, event_type = run_hygiene_action("unknown_action", level="L2", context={})
    assert result.status == "failed"
    assert event_type == "CRR_HYGIENE_EXECUTOR_FAILED"


def test_adapter_static_check_no_duplicate_transformation_logic():
    crr_root = Path(__file__).parents[2] / "hg_crr"
    scan_files = (
        "executor_adapter.py",
        "executors.py",
        "hygiene.py",
        "l1_cycle.py",
        "l2_l3_cycle.py",
        "eligibility.py",
        "drain.py",
        "rtc_adapter.py",
    )
    for name in scan_files:
        source = (crr_root / name).read_text(encoding="utf-8")
        assert not FORBIDDEN_HYGIENE_TOKENS.search(source), f"forbidden transform call in {name}"


def test_l2_cycle_emits_recovery_events(tmp_path: Path):
    recovery = Phase1RecoveryHandler(
        tmp_path / "checkpoints",
        level="L2",
        requested=True,
        manual=True,
        workspace_root=tmp_path,
    )
    loop = _loop(tmp_path, recovery)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l2"}, source="timer")
    assert loop.run_once(poll_timeout=0.0) == "recovery"

    event_types = {e["type"] for e in loop.bus.read_all()}
    assert "CRR_RECOVERY_ELIGIBILITY_EVALUATED" in event_types
    assert "CRR_RECOVERY_CYCLE_STARTED" in event_types
    assert "CRR_ADMISSION_PAUSED" in event_types
    assert "CRR_DRAIN_STARTED" in event_types
    assert "CRR_DRAIN_COMPLETED" in event_types
    assert "CRR_HYGIENE_EXECUTOR_STARTED" in event_types
    assert "CRR_REHYDRATION_LOAD_ORDER_VERIFIED" in event_types
    assert "CRR_RECOVERY_CYCLE_COMPLETED" in event_types


def test_l3_cycle_emits_recovery_events(tmp_path: Path):
    recovery = Phase1RecoveryHandler(
        tmp_path / "checkpoints",
        level="L3",
        requested=True,
        manual=True,
        workspace_root=tmp_path,
    )
    loop = _loop(tmp_path, recovery)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l3"}, source="timer")
    assert loop.run_once(poll_timeout=0.0) == "recovery"

    event_types = {e["type"] for e in loop.bus.read_all()}
    assert "CRR_RECOVERY_CYCLE_STARTED" in event_types
    assert "CRR_RECOVERY_CYCLE_COMPLETED" in event_types


def test_l2_checkpoint_rehydration_preserves_chains(tmp_path: Path):
    recovery = Phase1RecoveryHandler(
        tmp_path / "checkpoints",
        level="L2",
        requested=True,
        manual=True,
        workspace_root=tmp_path,
    )
    loop = _loop(tmp_path, recovery)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l2"}, source="timer")
    loop.run_once(poll_timeout=0.0)

    events = list(loop.bus.read_all())
    checkpoint = [e for e in events if e["type"] == "CRR_CHECKPOINT_RECORDED"][0]
    heads = checkpoint["payload"]["evidence_chain_heads"]
    verify = [e for e in events if e["type"] == "CRR_REHYDRATION_LOAD_ORDER_VERIFIED"][0]
    assert verify["payload"]["ok"] is True
    assert verify["payload"]["observed_heads"]["rtc_event_seq"] >= heads["rtc_event_seq"]


def test_l3_checkpoint_rehydration_preserves_chains(tmp_path: Path):
    recovery = Phase1RecoveryHandler(
        tmp_path / "checkpoints",
        level="L3",
        requested=True,
        manual=True,
        workspace_root=tmp_path,
    )
    loop = _loop(tmp_path, recovery)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l3"}, source="timer")
    loop.run_once(poll_timeout=0.0)

    verify = [
        e for e in loop.bus.read_all() if e["type"] == "CRR_REHYDRATION_LOAD_ORDER_VERIFIED"
    ][0]
    assert verify["payload"]["ok"] is True
    assert verify["payload"]["requires_dispatch_precheck"] is True


def test_rewind_fails_load_order_verification(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    manager = CheckpointManager(tmp_path / "checkpoints")
    world_state = {"self": {"ticks": 0}, "goals": {"pending_tasks": []}, "environment": {}}
    bus.submit("TIMER_EVENT", {"timer_id": "pre"}, source="timer")
    record = manager.create_from_runtime(
        bus=bus,
        world_state=world_state,
        checkpoint_id="ckpt_bad",
        cycle_ref="crr_bad",
        created_at="2026-06-11T03:00:01.000000Z",
    )
    future_head = "sha256:" + ("f" * 64)
    record.manifest["evidence_chain_heads"]["rtc_event_log"] = future_head
    record.manifest["evidence_chain_heads"]["rtc_event_seq"] = 999
    result = RehydrationVerifier().verify_load_order(record, bus=bus, world_state=world_state)
    assert result.ok is False
    assert result.reason_code in {
        "event_log_rewind_or_mismatch",
        "trusted_event_log_rewind_or_mismatch",
        "missing_observed_chain_head",
        "evidence_head_mismatch",
        "manifest_hash_mismatch",
    }


def test_panic_preempts_l2(tmp_path: Path):
    recovery = Phase1RecoveryHandler(tmp_path / "checkpoints", level="L2", requested=True, manual=True)
    loop = _loop(tmp_path, recovery)
    loop.panic.enter("test")
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l2"}, source="timer")
    assert loop.run_once(poll_timeout=0.0) == "panic"
    assert recovery.cycles == 0


def test_panic_preempts_l3(tmp_path: Path):
    recovery = Phase1RecoveryHandler(tmp_path / "checkpoints", level="L3", requested=True, manual=True)
    loop = _loop(tmp_path, recovery)
    loop.panic.enter("test")
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l3"}, source="timer")
    assert loop.run_once(poll_timeout=0.0) == "panic"
    assert recovery.cycles == 0


def test_safe_mode_preempts_l2(tmp_path: Path):
    recovery = Phase1RecoveryHandler(tmp_path / "checkpoints", level="L2", requested=True, manual=True)
    loop = _loop(tmp_path, recovery)
    recovery.enter_safe_state()
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l2"}, source="timer")
    assert loop.run_once(poll_timeout=0.0) == "tick"
    assert recovery.cycles == 0


def test_aep_high_severity_requests_but_cannot_force_l3():
    policy = RecoveryEligibilityPolicy(min_l3_interval=100)
    view = {"self": {"ticks": 1}, "environment": {}}
    aep = {"max_severity": 9}
    result = policy.evaluate(view=view, aep_state=aep, requested_level="L3", manual=False)
    assert result.aep_pressure is True
    assert result.allowed is True
    assert result.selected_level == "L2"
    assert result.reason_code == "aep_pressure_downgrade"


def test_eligibility_enforces_min_interval():
    state = EligibilityState(last_l2_tick=10)
    policy = RecoveryEligibilityPolicy(state=state, min_l2_interval=5)
    view = {"self": {"ticks": 12}, "environment": {}}
    result = policy.evaluate(view=view, aep_state={}, requested_level="L2", manual=False)
    assert result.allowed is False
    assert result.reason_code == "l2_min_interval"
    assert result.cooldown_until_tick == 15


def test_l3_escalation_cap_refused():
    state = EligibilityState(l3_count_in_window=2, window_start_tick=0)
    policy = RecoveryEligibilityPolicy(state=state, l3_escalation_cap=2)
    view = {"self": {"ticks": 5}, "environment": {}}
    result = policy.evaluate(view=view, aep_state={}, requested_level="L3", manual=False)
    assert result.allowed is False
    assert result.reason_code == "l3_escalation_cap"


def test_l3_escalation_cap_refused_emits_event(tmp_path: Path):
    state = EligibilityState(l3_count_in_window=2, window_start_tick=0)
    recovery = Phase1RecoveryHandler(
        tmp_path / "checkpoints",
        level="L3",
        requested=True,
        eligibility_state=state,
    )
    loop = _loop(tmp_path, recovery)
    loop.state["self"]["ticks"] = 5
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l3cap"}, source="timer")
    assert loop.run_once(poll_timeout=0.0) == "recovery"
    event_types = [e["type"] for e in loop.bus.read_all()]
    assert "CRR_RECOVERY_ESCALATION_REFUSED" in event_types
    assert "CRR_RECOVERY_CYCLE_STARTED" not in event_types
    assert recovery.cycles == 0


def test_pending_revoked_work_not_freshened(tmp_path: Path):
    recovery = Phase1RecoveryHandler(
        tmp_path / "checkpoints",
        level="L2",
        requested=True,
        manual=True,
        workspace_root=tmp_path,
    )
    loop = _loop(tmp_path, recovery)
    loop.state["goals"]["pending_tasks"] = [
        {"task_id": "t1", "revoked": True},
        {"task_id": "t2", "in_flight": True},
    ]
    pending_before = list(loop.state["goals"]["pending_tasks"])
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l2"}, source="timer")
    loop.run_once(poll_timeout=0.0)
    assert loop.state["goals"]["pending_tasks"] == pending_before


def test_l2_l3_replay_deterministic(tmp_path: Path):
    recovery = Phase1RecoveryHandler(
        tmp_path / "checkpoints",
        level="L2",
        requested=True,
        manual=True,
        workspace_root=tmp_path,
    )
    loop = _loop(tmp_path, recovery)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l2"}, source="timer")
    loop.run_once(poll_timeout=0.0)
    result = replay(tmp_path / "runtime")
    assert result.ok is True
    assert result.state["activity"]["crr"]["cycles"] == 1
    assert result.state["activity"]["crr"]["load_order_verifications"] == 1


def test_invoke_executor_when_enabled(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_CRR_INVOKE_EXECUTORS", "1")
    with mock.patch("hg_crr.executor_adapter._invoke_registered_executor", return_value=("completed", "mocked")):
        result, event_type = run_hygiene_action(
            "run_memory_maintenance",
            level="L2",
            context={"workspace_root": str(tmp_path)},
        )
    assert result.status == "completed"
    assert event_type == "CRR_HYGIENE_EXECUTOR_COMPLETED"


def test_skipped_executor_not_completed_by_default(tmp_path: Path):
    old = os.environ.pop("HG_CRR_INVOKE_EXECUTORS", None)
    try:
        result, event_type = run_hygiene_action(
            "run_memory_maintenance",
            level="L2",
            context={"workspace_root": str(tmp_path)},
        )
        assert result.status == "skipped_not_invoked"
        assert event_type == "CRR_HYGIENE_DELEGATED"
    finally:
        if old is not None:
            os.environ["HG_CRR_INVOKE_EXECUTORS"] = old


def test_crr_events_registered_in_event_types():
    from hg_runtime.bus import TypeRegistry

    registry = TypeRegistry()
    for name in (
        "CRR_RECOVERY_ELIGIBILITY_EVALUATED",
        "CRR_DRAIN_COMPLETED",
        "CRR_HYGIENE_EXECUTOR_STARTED",
        "CRR_REHYDRATION_LOAD_ORDER_VERIFIED",
        "CRR_RECOVERY_CYCLE_COMPLETED",
    ):
        assert name in registry
