"""Real soak launch schema tests."""
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict, load_launch_policy


def test_policy_phase_245():
    p = load_launch_policy()
    assert p["phase"] == "24.5"
    assert p["default_live_posts_allowed"] is False
    assert p["reply_allowed"] is False
