"""CRR Phase 1 L1 recovery cycle tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hg_crr import (
    L1CycleContext,
    L1CycleStateMachine,
    L1RecoveryOrchestrator,
    Phase1RecoveryHandler,
    delegate_l1_hygiene,
)
from hg_crr.checkpoint_manager import CheckpointManager
from hg_crr.cycle_states import L1_LEGAL_TRANSITIONS
from hg_crr.executor_adapter import L1_HYGIENE_ACTIONS
from hg_crr.trusted_snapshot import build_trusted_snapshot, runtime_config_hash
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
        return f"2026-06-11T02:00:{counter['value']:02d}.000000Z"

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


L1_TRANSITION_SEQUENCE = (
    "RECOVERY_REQUESTED",
    "DRAINING",
    "CHECKPOINTING",
    "HYGIENE_DELEGATING",
    "REHYDRATING",
    "RESUMED",
    "NORMAL",
)


def test_l1_state_machine_legal_transitions():
    fsm = L1CycleStateMachine()
    for target in L1_TRANSITION_SEQUENCE:
        fsm.transition(target, entered_at="t")
    assert fsm.state == "NORMAL"
    with pytest.raises(ValueError):
        fsm.transition("DRAINING", entered_at="t")


def test_l1_cycle_emits_state_transition_events(tmp_path: Path):
    recovery = Phase1RecoveryHandler(tmp_path / "checkpoints", requested=True)
    loop = _loop(tmp_path, recovery)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l1"}, source="timer")

    assert loop.run_once(poll_timeout=0.0) == "recovery"

    events = list(loop.bus.read_all())
    transitions = [
        (e["payload"]["from_state"], e["payload"]["to_state"])
        for e in events
        if e["type"] == "CRR_RECOVERY_STATE_TRANSITION"
    ]
    assert transitions == [
        ("NORMAL", "RECOVERY_REQUESTED"),
        ("RECOVERY_REQUESTED", "DRAINING"),
        ("DRAINING", "CHECKPOINTING"),
        ("CHECKPOINTING", "HYGIENE_DELEGATING"),
        ("HYGIENE_DELEGATING", "REHYDRATING"),
        ("REHYDRATING", "RESUMED"),
        ("RESUMED", "NORMAL"),
    ]
    event_types = {e["type"] for e in events}
    assert "CRR_HYGIENE_DELEGATED" in event_types
    assert "CRR_REHYDRATION_VERIFIED" in event_types
    assert "CRR_TRUSTED_SNAPSHOT_RECORDED" in event_types


def test_l1_recovery_rehydration_payload_includes_head_continuity(tmp_path: Path):
    recovery = Phase1RecoveryHandler(tmp_path / "checkpoints", requested=True)
    loop = _loop(tmp_path, recovery)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l1"}, source="timer")
    loop.run_once(poll_timeout=0.0)

    verify_events = [
        event for event in loop.bus.read_all() if event["type"] == "CRR_REHYDRATION_VERIFIED"
    ]
    assert len(verify_events) == 1
    payload = verify_events[0]["payload"]
    assert payload["ok"] is True
    assert payload["reason_code"] is None
    assert payload["expected_heads"]["rtc_event_log"]
    assert payload["observed_heads"]["rtc_event_log"]
    assert int(payload["observed_heads"]["rtc_event_seq"]) >= int(
        payload["expected_heads"]["rtc_event_seq"]
    )


def test_l1_pause_resume_preserves_replay_determinism(tmp_path: Path):
    recovery = Phase1RecoveryHandler(tmp_path / "checkpoints", requested=True)
    loop = _loop(tmp_path, recovery)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l1"}, source="timer")
    loop.run_once(poll_timeout=0.0)

    recovery.requested = False
    loop.bus.submit("TIMER_EVENT", {"timer_id": "post"}, source="timer")
    loop.run_once(poll_timeout=0.0)

    result = replay(tmp_path / "runtime")
    assert result.ok is True
    assert result.state["activity"]["crr"]["cycles"] == 1
    assert result.state["activity"]["crr"]["rehydration_verifications"] == 1
    assert result.state["activity"]["crr"]["state_transitions"] == 7
    assert result.state["self"]["ticks"] == 2
    assert result.state["environment"]["recovery_state"] == "NORMAL"


def test_evidence_chain_heads_grown_only_never_rewound(tmp_path: Path):
    recovery = Phase1RecoveryHandler(tmp_path / "checkpoints", requested=True)
    loop = _loop(tmp_path, recovery)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l1"}, source="timer")
    loop.run_once(poll_timeout=0.0)

    events = list(loop.bus.read_all())
    checkpoint_events = [e for e in events if e["type"] == "CRR_CHECKPOINT_RECORDED"]
    assert len(checkpoint_events) == 1
    heads = checkpoint_events[0]["payload"]["evidence_chain_heads"]
    first_head = heads["rtc_event_log"]
    first_seq = heads["rtc_event_seq"]

    recovery.requested = True
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l1b"}, source="timer")
    loop.run_once(poll_timeout=0.0)

    events2 = list(loop.bus.read_all())
    checkpoint_events2 = [e for e in events2 if e["type"] == "CRR_CHECKPOINT_RECORDED"]
    assert len(checkpoint_events2) == 2
    heads2 = checkpoint_events2[1]["payload"]["evidence_chain_heads"]
    assert heads2["rtc_event_seq"] > first_seq
    assert heads2["rtc_event_log"] != first_head

    manager = CheckpointManager(tmp_path / "checkpoints")
    record = manager.load(recovery.last_manifest["checkpoint_id"])
    assert manager.validate_continuity(record, bus=loop.bus, world_state=loop.state) is True


FORBIDDEN_HYGIENE_TOKENS = re.compile(
    r"\b(flush|compact|gc|prune|evict|archive|compact_session)\s*\(",
    re.IGNORECASE,
)


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

    for action in L1_HYGIENE_ACTIONS:
        result = delegate_l1_hygiene(action, context={"cycle_id": "test"})
        assert result.status == "delegated_not_invoked"
        assert "hg_core" in result.executor_ref or result.executor in {
            "cache_eviction",
            "memory_maintenance",
        }


def test_pending_work_not_freshened_by_recovery(tmp_path: Path):
    recovery = Phase1RecoveryHandler(tmp_path / "checkpoints", requested=True)
    loop = _loop(tmp_path, recovery)
    loop.state["goals"]["pending_tasks"] = [
        {"task_id": "t1", "status": "pending", "revoked": True},
        {"task_id": "t2", "status": "pending"},
    ]
    pending_before = list(loop.state["goals"]["pending_tasks"])
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l1"}, source="timer")
    loop.run_once(poll_timeout=0.0)

    assert loop.state["goals"]["pending_tasks"] == pending_before
    checkpoint = recovery.last_manifest
    queues_path = tmp_path / "checkpoints" / checkpoint["checkpoint_id"] / "queues.json"
    import json

    queues = json.loads(queues_path.read_text(encoding="utf-8"))
    assert queues["pending_tasks"] == pending_before


def test_panic_preempts_recovery_before_cycle(tmp_path: Path):
    recovery = Phase1RecoveryHandler(tmp_path / "checkpoints", requested=True)
    loop = _loop(tmp_path, recovery)
    loop.panic.enter("test")
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l1"}, source="timer")

    assert loop.run_once(poll_timeout=0.0) == "panic"
    assert recovery.safe_state is True
    assert not list((tmp_path / "checkpoints").glob("*/manifest.json"))


def test_fsm_panic_preempts_mid_cycle():
    fsm = L1CycleStateMachine()
    fsm.transition("RECOVERY_REQUESTED", entered_at="t")
    fsm.transition("DRAINING", entered_at="t")
    fsm.panic_active = True
    assert fsm.transition("CHECKPOINTING", entered_at="t") == "RECOVERY_FAILED"
    assert fsm.preempt("panic", entered_at="t") == "RECOVERY_FAILED"


def test_fsm_safe_mode_preempts_mid_cycle():
    fsm = L1CycleStateMachine()
    fsm.transition("RECOVERY_REQUESTED", entered_at="t")
    fsm.transition("DRAINING", entered_at="t")
    fsm.safe_mode_active = True
    assert fsm.transition("CHECKPOINTING", entered_at="t") == "RECOVERY_FAILED"
    assert fsm.preempt("safe_mode", entered_at="t") == "RECOVERY_FAILED"


def test_safe_mode_preempts_recovery_before_cycle(tmp_path: Path):
    recovery = Phase1RecoveryHandler(tmp_path / "checkpoints", requested=True)
    loop = _loop(tmp_path, recovery)
    recovery.enter_safe_state()
    loop.bus.submit("TIMER_EVENT", {"timer_id": "l1"}, source="timer")

    assert loop.run_once(poll_timeout=0.0) == "tick"
    assert recovery.safe_state is True
    assert recovery.cycles == 0
    assert not list((tmp_path / "checkpoints").glob("*/manifest.json"))
    event_types = [event["type"] for event in loop.bus.read_all()]
    assert "CRR_TRIGGER_DECIDED" not in event_types


def test_handler_safe_mode_preempts_active_orchestrator_mid_cycle(tmp_path: Path):
    recovery = Phase1RecoveryHandler(tmp_path / "checkpoints", requested=True)
    context = L1CycleContext(
        checkpoint_manager=recovery.checkpoint_manager,
        trusted_registry=recovery.trusted_registry,
    )
    orchestrator = L1RecoveryOrchestrator(context)
    orchestrator.fsm.transition("RECOVERY_REQUESTED", entered_at="t")
    orchestrator.fsm.transition("DRAINING", entered_at="t")
    recovery._orchestrator = orchestrator

    recovery.enter_safe_state()

    assert orchestrator.fsm.safe_mode_active is True
    assert orchestrator.fsm.state == "RECOVERY_FAILED"
    assert recovery.safe_state is True


def test_trusted_snapshot_manifest_fields(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    manager = CheckpointManager(tmp_path / "checkpoints")
    world_state = {"self": {"ticks": 0}, "goals": {"pending_tasks": []}, "environment": {}}
    record = manager.create_from_runtime(
        bus=bus,
        world_state=world_state,
        checkpoint_id="ckpt_ts",
        cycle_ref="crr_ts",
        created_at="2026-06-11T02:00:01.000000Z",
    )
    trusted = build_trusted_snapshot(
        record,
        snapshot_id="tsnap_1",
        runtime_config_hash=runtime_config_hash({"schema": "rtc-runtime-config"}),
        promoted_at="2026-06-11T02:00:02.000000Z",
    )
    payload = trusted.to_payload()
    assert payload["event_log_head"].startswith("sha256:")
    assert payload["world_state_hash"]
    assert payload["runtime_config_hash"].startswith("sha256:")
    assert "evidence_chain_heads" in payload
