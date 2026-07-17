from __future__ import annotations

from pathlib import Path

from hg_aep import AEPSignal, emit_signal_event, reconstruct_arousal_state
from hg_aep.replay import signals_from_rtc_events
from hg_runtime.bus import EventBus
from hg_runtime.replay import replay


NOW = "2026-06-11T03:00:00.000000Z"


def _signal(**overrides) -> AEPSignal:
    payload = {
        "signal_id": "aep_replay_1",
        "signal_class": "RESOURCE_PRESSURE",
        "severity": 7,
        "scope": "global",
        "source": {"component": "platform.health", "ref": "health:1"},
        "evidence_refs": ("health:1",),
        "emitted_at": NOW,
        "causal_parents": ("evt_parent",),
    }
    payload.update(overrides)
    return AEPSignal(**payload)


def test_aep_state_reconstructs_from_event_log(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=lambda: NOW)
    emit_signal_event(bus, _signal())
    emit_signal_event(
        bus,
        _signal(
            signal_id="aep_replay_2",
            signal_class="UNCERTAINTY",
            severity=4,
            source={"component": "platform.observations"},
        ),
    )
    events = list(bus.read_all())
    reconstructed = reconstruct_arousal_state(events, computed_at=NOW)
    assert reconstructed["levels"]["RESOURCE_PRESSURE"] == 7
    assert reconstructed["levels"]["UNCERTAINTY"] == 4
    assert reconstructed["max_severity"] == 7
    assert len(signals_from_rtc_events(events)) == 2


def test_replay_matches_runtime_arousal_counters(tmp_path: Path):
    bus = EventBus(tmp_path / "runtime", clock=lambda: NOW)
    emit_signal_event(bus, _signal())
    result = replay(tmp_path / "runtime")
    assert result.ok is True
    assert result.state["activity"]["aep"]["signals"] == 1
    assert result.state["environment"]["arousal"]["max_severity"] == 7
