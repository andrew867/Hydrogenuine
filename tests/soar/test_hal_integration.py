"""SOAR Phase 1 + HAL + RTC integration tests."""

from __future__ import annotations

from pathlib import Path

from hg_core.governance.permit_binder import PermitBinder
from hg_core.governance.trace_emitter import TraceEmitter
from hg_runtime.bus import EventBus
from hg_runtime.handlers import Phase1HALDecisionHandler, StubCognitionHandler
from hg_runtime.handlers.stubs import StubArousalReader, StubKernelHandler, StubMemoryHandler, StubRecoveryHandler
from hg_runtime.loop import RuntimeLoop
from hg_runtime.replay import replay


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T16:00:{counter['value']:02d}.000000Z"

    return tick


def test_hal_handler_emits_soar_then_hal_events(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_SOAR_ENABLED", "1")
    monkeypatch.setenv("HG_HAL_ENABLED", "1")
    trace = TraceEmitter(tmp_path / "gpp" / "trace.jsonl", enabled=True, clock=_clock())
    handler = Phase1HALDecisionHandler(permit_binder=PermitBinder(trace_emitter=trace, clock=_clock()))
    loop = RuntimeLoop(
        EventBus(tmp_path / "runtime", clock=_clock()),
        cognition=StubCognitionHandler(),
        decision=handler,
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=StubArousalReader(),
        recovery=StubRecoveryHandler(),
        runtime_dir=tmp_path / "runtime",
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )
    loop.bus.submit(
        "CHAT_MESSAGE",
        {"session_id": "s1", "role": "user", "content": "soar"},
        source="plt.chat",
    )
    loop.run_once(poll_timeout=0.0)
    types = [event["type"] for event in loop.bus.read_all()]
    assert types.count("SOAR_DOMAIN_EVALUATED") == 7
    assert "SOAR_D7_DECISION_RECORDED" in types
    assert "SOAR_D7_CRITIQUE_RECORDED" in types
    assert "HAL_ARBITRATION_REQUESTED" in types
    assert "HAL_ARBITRATION_RECORDED" in types
    assert types.index("SOAR_D7_CRITIQUE_RECORDED") < types.index("HAL_ARBITRATION_REQUESTED")
    decision = next(event for event in loop.bus.read_all() if event["type"] == "DECISION_EVENT")
    assert decision["payload"].get("soar_run_ref")
    assert replay(tmp_path / "runtime").ok is True
