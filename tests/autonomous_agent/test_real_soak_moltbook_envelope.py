"""Moltbook envelope tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hg_runtime.real_soak_launch.moltbook_envelope import (
    MoltbookLiveEnvelope,
    create_template_envelope,
    zero_may_modify_envelope_field,
)


def test_default_max_live_posts_zero():
    env = create_template_envelope(soak_id="t1")
    assert env.max_live_posts == 0


def test_platform_moltbook():
    env = create_template_envelope(soak_id="t2")
    assert env.platform == "moltbook"
    assert env.allowed_action_type == "publish_post"


def test_zero_cannot_increase_quota():
    env = create_template_envelope(soak_id="t3", max_live_posts=1)
    assert zero_may_modify_envelope_field("max_live_posts", 5, env) is False


def test_zero_cannot_change_platform():
    env = create_template_envelope(soak_id="t4")
    assert zero_may_modify_envelope_field("platform", "twitter", env) is False


def test_finite_valid_until():
    now = datetime.now(timezone.utc)
    env = MoltbookLiveEnvelope(
        envelope_id="e1",
        valid_from=now.isoformat(),
        valid_until=(now + timedelta(hours=1)).isoformat(),
        max_live_posts=0,
    )
    assert not env.is_expired()
