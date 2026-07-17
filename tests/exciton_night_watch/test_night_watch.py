"""Night watch safe-to-step-away."""

from __future__ import annotations

from hg_runtime.exciton.night_watch import build_night_watch, compute_safe_to_step_away
from hg_runtime.exciton.status_aggregator import AggregatorConfig, build_snapshot


def test_night_watch_computed_field():
    snap = build_snapshot(AggregatorConfig(offline_fixture=True))
    nw = build_night_watch(panels=snap.panels)
    assert "safe_to_step_away" in nw
    assert isinstance(nw["safe_blockers"], list)


def test_safe_false_on_red_panel():
    from hg_runtime.exciton.schema import ExcitonPanelState

    class P:
        panel_id = "X"
        state = ExcitonPanelState.RED
        fields = {}

    soak = {"active": True, "observer_verdict": "GREEN_OBSERVER", "stop_available": True,
            "panic_available": True, "forbidden_action_count": 0, "credential_leak_count": 0,
            "publish_enabled": False, "operator_confirmed_after_observation": False,
            "operator_confirmation_required": False, "panic_file_present": False, "stop_file_present": False}
    safe, blockers = compute_safe_to_step_away(panels=[P()], soak=soak, activity={})
    assert safe is False
    assert any("red_panel" in b for b in blockers)
