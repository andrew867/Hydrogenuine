"""Always-on organ inference supervisor tests."""

from __future__ import annotations

from hg_runtime.model_provider_fabric.always_on_supervisor import (
    AlwaysOnOrganSupervisor,
    OrganLoopBudget,
)


def test_bounded_loop_stops() -> None:
    clock = {"t": 0.0}

    def fake_clock() -> float:
        return clock["t"]

    sup = AlwaysOnOrganSupervisor(
        organ_id="organ:HRT",
        role="ORGAN_BACKGROUND",
        budget=OrganLoopBudget(max_duration_seconds=10, max_iterations=3, heartbeat_interval_seconds=2),
    )

    def infer(_task) -> str:
        clock["t"] += 4.0
        return "ok"

    report = sup.run_bounded_loop(infer_fn=infer, clock=fake_clock)
    assert report["iterations"] <= 3
    assert report["unbounded_loop"] is False
    assert any(e["event_kind"] == "MODEL_RESPONSE_COMPLETED" for e in report["events"])


def test_panic_stop() -> None:
    sup = AlwaysOnOrganSupervisor(organ_id="organ:HRT", role="ORGAN_BACKGROUND", budget=OrganLoopBudget(max_iterations=100))
    sup.panic_stop()
    clock = {"t": 0.0}
    report = sup.run_bounded_loop(clock=lambda: clock["t"])
    assert report["stop"]["panic"] is True


def test_token_bus_events_metadata() -> None:
    sup = AlwaysOnOrganSupervisor(organ_id="organ:RSP", role="ORGAN_BACKGROUND", budget=OrganLoopBudget(max_iterations=1))
    clock = {"t": 0.0}
    report = sup.run_bounded_loop(infer_fn=lambda t: "tok", clock=lambda: clock.__setitem__("t", clock["t"] + 1) or clock["t"])
    for event in report["events"]:
        assert event["advisory_only"] is True
        assert event["permission_granted"] is False
