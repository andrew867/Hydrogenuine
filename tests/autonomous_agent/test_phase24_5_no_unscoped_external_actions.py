"""No unscoped external actions."""
from hg_runtime.real_soak_launch.live_post_guard import evaluate_live_post_guard, FORBIDDEN_ACTIONS
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict


def test_mass_message_refused():
    d = evaluate_live_post_guard(envelope=None, action_type="mass_message")
    assert RealSoakLaunchVerdict.RED_FORBIDDEN_ACTION.value in d.refusal_reasons


def test_hardware_refused():
    d = evaluate_live_post_guard(envelope=None, action_type="hardware")
    assert RealSoakLaunchVerdict.RED_FORBIDDEN_ACTION.value in d.refusal_reasons


def test_forbidden_set():
    assert "send" in FORBIDDEN_ACTIONS
    assert "browser" in FORBIDDEN_ACTIONS
