"""RTC Phase 1 — persistent loop controller and lifecycle health events."""

from __future__ import annotations

from pathlib import Path

import pytest

from hg_runtime.config import RuntimeConfig
from hg_runtime.controller import PersistentLoopController
from hg_runtime.handlers.registry import HandlerRegistry
from hg_runtime.loop import STAGES
from hg_runtime.replay import replay
from hg_runtime import world_state as ws


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T08:00:{counter['value']:02d}.000000Z"

    return tick


def _config(tmp_path: Path, *, stage_hook=None) -> RuntimeConfig:
    return RuntimeConfig(
        runtime_dir=tmp_path / "runtime",
        max_ticks=3,
        idle_block_s=0.0,
        require_enabled=False,
        phase1_lifecycle=True,
    )


def _controller(tmp_path: Path, *, stage_hook=None) -> PersistentLoopController:
    config = _config(tmp_path)
    controller = PersistentLoopController(config)
    if stage_hook is not None:
        controller.loop._stage_hook = stage_hook
    return controller


def _submit_chat(controller: PersistentLoopController, content: str) -> None:
    controller.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": content},
        source="plt.chat",
    )


def test_bounded_persistent_loop_runs_n_ticks_and_stops_cleanly(tmp_path: Path):
    controller = _controller(tmp_path)
    for index in range(3):
        _submit_chat(controller, f"tick-{index + 1}")
        assert controller.run_once(poll_timeout=0.0) == "tick"
    controller.loop.stop(reason="test_complete")

    events = list(controller.bus.read_all())
    types = [event["type"] for event in events]
    assert types.count("RUNTIME_TICK_STARTED") == 3
    assert types.count("RUNTIME_TICK_COMPLETED") == 3
    assert "RUNTIME_STOP_REQUESTED" in types
    assert "RUNTIME_STOPPED" in types
    assert types.index("RUNTIME_STOP_REQUESTED") < types.index("RUNTIME_STOPPED")
    assert controller.loop.state["self"]["ticks"] == 3
    assert replay(tmp_path / "runtime").ok is True


def test_panic_before_tick_prevents_handler_execution(tmp_path: Path):
    controller = _controller(tmp_path)
    _submit_chat(controller, "blocked")
    controller.panic.enter("test")
    assert controller.run_once(poll_timeout=0.0) == "panic"

    types = [event["type"] for event in controller.bus.read_all()]
    assert "RUNTIME_PANIC_BLOCKED" in types
    assert "PANIC_ENTERED" in types
    assert "CHAT_MESSAGE" not in types
    assert "RUNTIME_TICK_STARTED" not in types
    assert "PROPOSAL_EMITTED" not in types
    assert controller.loop.cognition.halted is True
    assert controller.loop.kernel.blocked is True
    assert controller.loop.cognition.calls == 0


def test_replay_reconstructs_same_world_state(tmp_path: Path):
    controller = _controller(tmp_path)
    _submit_chat(controller, "replay")
    controller.run_once(poll_timeout=0.0)
    controller.loop.stop(reason="test")

    events = list(controller.bus.read_all())
    rebuilt = ws.apply_many(ws.initial_state(), events)
    result = replay(tmp_path / "runtime")

    assert result.ok is True
    assert result.state == rebuilt
    assert result.state_hash == ws.state_hash(controller.loop.state)


def test_event_ordering_is_deterministic(tmp_path: Path):
    stages: list[str] = []
    controller = _controller(tmp_path, stage_hook=stages.append)
    _submit_chat(controller, "order")
    controller.run_once(poll_timeout=0.0)

    types = [event["type"] for event in controller.bus.read_all()]
    assert stages[: len(STAGES)] == STAGES
    assert stages[0] == "panic_check"
    tick_started = types.index("RUNTIME_TICK_STARTED")
    proposal = types.index("PROPOSAL_EMITTED")
    tick_completed = types.index("RUNTIME_TICK_COMPLETED")
    assert tick_started < proposal < tick_completed


def test_handler_registry_cannot_bypass_event_bus():
    forbidden = ("bus.emit(", "EventBus(")
    for path in Path("hg_runtime/handlers").rglob("*.py"):
        if path.name == "__init__.py":
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path} must not bypass RTC bus via {token}"


def test_handler_registry_wires_ueak_and_oea_stubs():
    registry = HandlerRegistry.phase0_stubs()
    assert registry.ueak is registry.kernel._ueak
    assert registry.oea is registry.kernel._oea
    assert registry.cognition.handler_id
    assert registry.decision.handler_id


def test_run_bounded_stops_after_limit(tmp_path: Path):
    controller = _controller(tmp_path)
    _submit_chat(controller, "bounded")
    assert controller.run_bounded(max_ticks=1) == 0
    assert controller.loop.state["self"]["ticks"] == 1
    types = [event["type"] for event in controller.bus.read_all()]
    assert "RUNTIME_STOPPED" in types
    assert replay(tmp_path / "runtime").ok is True


def test_runtime_config_rejects_conflicting_run_modes(tmp_path: Path):
    with pytest.raises(ValueError, match="not both"):
        RuntimeConfig(
            runtime_dir=tmp_path / "runtime",
            max_ticks=5,
            run_until_stopped=True,
        )
