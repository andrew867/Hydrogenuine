"""Runtime stop and cleanup tests."""

from __future__ import annotations

from hg_runtime.agent0_dev_boot.stop_controller import RuntimeStopController


def test_panic_stop() -> None:
    ctrl = RuntimeStopController(run_id="t", max_duration_seconds=60)
    ctrl.panic_stop()
    assert ctrl.stopped
    assert ctrl.stop_reason == "panic_stop"


def test_budget_exceeded() -> None:
    ctrl = RuntimeStopController(run_id="t", max_duration_seconds=10)
    assert ctrl.budget_exceeded(0.0, lambda: 11.0)


def test_cleanup_receipt() -> None:
    ctrl = RuntimeStopController(run_id="t")
    receipt = ctrl.cleanup_receipt()
    assert receipt["permission_granted"] is False
