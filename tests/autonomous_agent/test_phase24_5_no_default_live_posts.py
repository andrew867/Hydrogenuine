"""No default live posts."""
from hg_runtime.real_soak_launch.live_post_guard import evaluate_live_post_guard
from hg_runtime.real_soak_launch.moltbook_envelope import create_template_envelope
from hg_runtime.real_soak_launch.schema import load_launch_policy


def test_policy_default_no_live():
    assert load_launch_policy()["default_live_posts_allowed"] is False


def test_template_zero():
    assert create_template_envelope(soak_id="d1").max_live_posts == 0


def test_guard_refuses_without_live_env():
    env = create_template_envelope(soak_id="d2", max_live_posts=1)
    env = type(env)(**{**env.__dict__, "status": "armed"})
    d = evaluate_live_post_guard(envelope=env, candidate_receipt_ref="c", permit_receipt_ref="p", content_hash="h")
    assert not d.allowed
