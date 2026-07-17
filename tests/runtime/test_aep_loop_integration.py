"""AEP Phase 2 — arousal processor wired into RTC loop tick."""

from __future__ import annotations

from pathlib import Path

from hg_aep.types import AEPSignal
from hg_runtime.bus import EventBus
from hg_runtime.handlers import (
    Phase1AEPArousalHandler,
    StubCognitionHandler,
    StubDecisionHandler,
    StubKernelHandler,
    StubMemoryHandler,
    StubRecoveryHandler,
)
from hg_runtime.loop import RuntimeLoop
from hg_runtime.replay import replay


NOW = "2026-06-11T12:00:00.000000Z"


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T12:00:{counter['value']:02d}.000000Z"

    return tick


def _loop(tmp_path: Path) -> RuntimeLoop:
    bus = EventBus(tmp_path / "runtime", clock=_clock())
    return RuntimeLoop(
        bus,
        cognition=StubCognitionHandler(),
        decision=StubDecisionHandler(),
        kernel=StubKernelHandler(),
        memory=StubMemoryHandler(),
        arousal=Phase1AEPArousalHandler(),
        recovery=StubRecoveryHandler(),
        runtime_dir=tmp_path / "runtime",
        idle_block_s=0.0,
        snapshot_every_ticks=0,
        require_enabled=False,
    )


def _submit_signal(bus: EventBus, *, severity: int = 7) -> None:
    signal = AEPSignal(
        signal_id="aep_loop_1",
        signal_class="RESOURCE_PRESSURE",
        severity=severity,
        scope="global",
        source={"component": "platform.health", "ref": "health:1"},
        evidence_refs=("health:1",),
        emitted_at=NOW,
        causal_parents=(),
    )
    bus.submit(
        "AEP_SIGNAL_EMITTED",
        signal.to_payload(),
        source="aep:platform.health",
        severity=severity,
    )


def test_aep_signal_emitted_processed_on_tick(tmp_path: Path):
    loop = _loop(tmp_path)
    _submit_signal(loop.bus)
    loop.bus.submit(
        "TIMER_EVENT",
        {"timer_id": "wake"},
        source="timer",
    )
    loop.run_once(poll_timeout=0.0)

    types = [event["type"] for event in loop.bus.read_all()]
    assert "AEP_SIGNAL_EMITTED" in types
    assert "AEP_SIGNAL_RECORDED" in types
    assert "AEP_AROUSAL_STATE_UPDATED" in types
    assert "AEP_MODULATION_RECORDED" in types
    assert types.index("AEP_SIGNAL_EMITTED") < types.index("AEP_SIGNAL_RECORDED")


def test_aep_modulation_has_no_authority_fields(tmp_path: Path):
    loop = _loop(tmp_path)
    _submit_signal(loop.bus, severity=8)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "wake"}, source="timer")
    loop.run_once(poll_timeout=0.0)

    forbidden = {"grant", "permit", "allow", "deny", "approve", "verdict", "decision"}
    for event in loop.bus.read_all():
        if event["type"] != "AEP_MODULATION_RECORDED":
            continue
        assert forbidden.isdisjoint(event.get("payload", {}))


def test_aep_processor_replayable(tmp_path: Path):
    loop = _loop(tmp_path)
    _submit_signal(loop.bus)
    loop.bus.submit("TIMER_EVENT", {"timer_id": "wake"}, source="timer")
    loop.run_once(poll_timeout=0.0)
    result = replay(tmp_path / "runtime")
    assert result.ok is True
    assert result.state["activity"]["aep"]["signals_recorded"] >= 1
