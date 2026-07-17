from __future__ import annotations

import os
from pathlib import Path
from types import MappingProxyType

import pytest

from hg_runtime.bus import BusError, EventBus
from hg_runtime.demo import build_loop
from hg_runtime.handlers import (
    StubArousalReader,
    StubCognitionHandler,
    StubDecisionHandler,
    StubKernelHandler,
    StubMemoryHandler,
    StubRecoveryHandler,
)
from hg_runtime.loop import STAGES, RuntimeLoop
from hg_runtime.replay import replay
from hg_runtime import world_state as ws
from hg_core.governance.trace_emitter import TraceEmitter, validate_chain as validate_trace_chain


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T00:00:{counter['value']:02d}.000000Z"

    return tick


def _loop(tmp_path: Path, *, stage_hook=None, governance_trace=None) -> RuntimeLoop:
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    return RuntimeLoop(
        bus,
        cognition=StubCognitionHandler(),
        decision=StubDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=StubArousalReader(),
        recovery=StubRecoveryHandler(),
        runtime_dir=tmp_path / "runtime",
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        stage_hook=stage_hook,
        governance_trace=governance_trace,
        require_enabled=False,
    )


def test_bus_rejects_unknown_event_type(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    with pytest.raises(BusError):
        bus.emit("NOT_REGISTERED", {}, source="test:rtc")


def test_bus_returns_deep_immutable_live_event_objects(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    event = bus.emit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "nested": {"value": 1}},
        source="test:rtc",
        causal_parents=["parent"],
    )

    assert isinstance(event, MappingProxyType)
    assert isinstance(event["payload"], MappingProxyType)
    assert isinstance(event["payload"]["nested"], MappingProxyType)
    assert event["causal_parents"] == ("parent",)
    with pytest.raises(TypeError):
        event["payload"] = {}
    with pytest.raises(TypeError):
        event["payload"]["nested"]["value"] = 2


def test_bus_overflow_reports_events_dropped(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=_clock(), queue_capacity=1)

    assert bus.submit("FILE_WATCH", {"path": "low"}, source="watch") is True
    assert bus.submit("CHAT_MESSAGE", {"content": "high"}, source="chat") is True

    events = bus.poll(timeout=0.0)
    assert [event["type"] for event in events] == ["EVENTS_DROPPED", "CHAT_MESSAGE"]
    assert events[0]["payload"]["dropped"] == {"FILE_WATCH": 1}
    assert bus.verify_chain()["ok"] is True


def test_event_chain_validates_and_reducer_is_replayable(tmp_path: Path):
    loop = _loop(tmp_path)
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "hello"},
        source="plt.chat",
    )

    assert loop.run_once(poll_timeout=0.0) == "tick"
    assert loop.bus.verify_chain()["ok"] is True

    events = list(loop.bus.read_all())
    reduced = ws.apply_many(ws.initial_state(), events)
    result = replay(tmp_path / "runtime")

    assert result.ok is True
    assert result.state == reduced
    assert result.state_hash == ws.state_hash(loop.state)


def test_phase0_vertical_slice_event_to_action_to_replay(tmp_path: Path):
    loop = _loop(tmp_path)
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "do phase0"},
        source="plt.chat",
    )

    loop.run_once(poll_timeout=0.0)
    events = list(loop.bus.read_all())
    event_types = [event["type"] for event in events]

    assert "CHAT_MESSAGE" in event_types
    assert "PROPOSAL_EMITTED" in event_types
    assert "DECISION_EVENT" in event_types
    assert "UEAK_EXECUTION_COMMITTED" in event_types
    assert "OEA_EFFECT_STUB_RECORDED" in event_types
    assert "MEMORY_RETRIEVED" in event_types
    assert "MEMORY_WRITTEN" in event_types
    assert event_types[-1] == "TICK_COMPLETED"
    assert loop.state["activity"]["memory"]["retrieved"] == 1
    assert loop.state["activity"]["memory"]["written"] == 1
    assert loop.state["activity"]["recent_memory_retrievals"][0]["query"] == "phase0_recent_events"
    assert replay(tmp_path / "runtime").ok is True


def test_runtime_stage_order_has_panic_at_step_zero(tmp_path: Path):
    stages = []
    loop = _loop(tmp_path, stage_hook=stages.append)
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "order"},
        source="plt.chat",
    )

    loop.run_once(poll_timeout=0.0)

    assert stages[: len(STAGES)] == STAGES
    assert stages[0] == "panic_check"


def test_timer_event_skips_cognition(tmp_path: Path):
    loop = _loop(tmp_path)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "phase0"}, source="timer")

    loop.run_once(poll_timeout=0.0)

    assert loop.cognition.calls == 0
    event_types = [event["type"] for event in loop.bus.read_all()]
    assert "PROPOSAL_EMITTED" not in event_types
    assert "TICK_COMPLETED" in event_types


def test_handlers_do_not_import_runtime_control_paths():
    forbidden = (
        "hg_runtime.bus",
        "hg_runtime.loop",
        "hg_runtime.replay",
        "hg_runtime.world_state",
    )

    handlers_dir = Path(__file__).parents[2] / "hg_runtime" / "handlers"
    for path in handlers_dir.glob("*.py"):
        if path.name in {"__init__.py", "registry.py"}:
            continue
        text = path.read_text(encoding="utf-8")
        for import_path in forbidden:
            assert import_path not in text


def test_panic_short_circuits_before_poll(tmp_path: Path):
    loop = _loop(tmp_path)
    loop.panic.enter("test")
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "blocked"},
        source="plt.chat",
    )

    assert loop.run_once(poll_timeout=0.0) == "panic"

    event_types = [event["type"] for event in loop.bus.read_all()]
    assert "PANIC_ENTERED" in event_types
    assert "CHAT_MESSAGE" not in event_types
    assert loop.cognition.halted is True
    assert loop.kernel.blocked is True


def test_demo_runs_finite_ticks_and_replays(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_RTC_ENABLED", "1")
    runtime_dir = tmp_path / "demo-runtime"
    loop = build_loop(runtime_dir, require_enabled=False)
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "demo", "role": "user", "content": "demo"},
        source="plt.chat",
    )
    assert loop.run_once(poll_timeout=0.0) == "tick"

    assert list(runtime_dir.glob("events-*.jsonl"))
    assert replay(runtime_dir).ok is True


def test_rtc_wires_gpp_phase0_trace_refs_without_enforcement(tmp_path: Path):
    trace = TraceEmitter(tmp_path / "gpp" / "governance_trace.jsonl", enabled=True, clock=_clock())
    loop = _loop(tmp_path, governance_trace=trace)
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "trace me"},
        source="plt.chat",
    )

    loop.run_once(poll_timeout=0.0)

    events = list(loop.bus.read_all())
    trace_events = [event for event in events if event["type"] == "GOVERNANCE_TRACE_RECORDED"]
    assert len(trace_events) == 1
    assert trace_events[0]["payload"]["enforcement"] == "none_phase0_trace_only"
    assert validate_trace_chain(trace.path).ok is True
    assert loop.state["activity"]["governance"]["trace_records"] == 1
    assert replay(tmp_path / "runtime").ok is True
