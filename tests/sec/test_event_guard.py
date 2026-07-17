"""CT-02 SEC-U2 event emission guard tests."""

from __future__ import annotations

import pytest

from hg_core.secrets.canary import CANARY_MARKERS
from hg_core.secrets.events import SecretEmissionRefused, guard_event_payload
from hg_runtime.bus import BusError, EventBus


def test_sec_u2_canary_event_refused() -> None:
    with pytest.raises(SecretEmissionRefused, match="canary"):
        guard_event_payload({"note": CANARY_MARKERS["event"]})


def test_sec_u2_bus_emit_refuses_canary(tmp_path) -> None:
    bus = EventBus(tmp_path / "runtime")
    with pytest.raises(BusError, match="secret_emission_refused"):
        bus.emit("TIMER_EVENT", {"timer_id": CANARY_MARKERS["event"]}, source="sec:test")


def test_normal_event_allowed(tmp_path) -> None:
    bus = EventBus(tmp_path / "runtime")
    event = bus.emit("TIMER_EVENT", {"timer_id": "safe-timer"}, source="sec:test")
    assert event["type"] == "TIMER_EVENT"
