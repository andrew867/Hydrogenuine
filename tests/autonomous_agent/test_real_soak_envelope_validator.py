"""Envelope validator tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hg_runtime.real_soak_launch.envelope_validator import validate_moltbook_envelope
from hg_runtime.real_soak_launch.moltbook_envelope import MoltbookLiveEnvelope
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict


def _env(**kw) -> MoltbookLiveEnvelope:
    now = datetime.now(timezone.utc)
    defaults = dict(
        envelope_id="v1",
        platform="moltbook",
        allowed_action_type="publish_post",
        max_live_posts=0,
        max_posts_per_hour=1,
        valid_from=now.isoformat(),
        valid_until=(now + timedelta(hours=2)).isoformat(),
    )
    defaults.update(kw)
    return MoltbookLiveEnvelope(**defaults)


def test_validate_zero_posts_yellow():
    d = validate_moltbook_envelope(_env(max_live_posts=0))
    assert d.valid
    assert RealSoakLaunchVerdict.YELLOW_QUOTA_ZERO.value in d.verdict


def test_validate_one_post():
    d = validate_moltbook_envelope(_env(max_live_posts=1))
    assert d.valid


def test_reject_wrong_platform():
    d = validate_moltbook_envelope(_env(platform="twitter"))
    assert not d.valid


def test_reject_no_valid_until():
    d = validate_moltbook_envelope(_env(valid_until=""))
    assert not d.valid
