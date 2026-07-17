"""Hands-off session config validation."""
from __future__ import annotations

import pytest

from hg_runtime.hands_off_session.errors import HandsOffConfigError
from hg_runtime.hands_off_session.session_config import HandsOffSessionConfig, validate_session_config


def _cfg(**kwargs) -> HandsOffSessionConfig:
    base = dict(
        session_id="s1",
        agent_id="zero",
        objective_universe_ref="u1",
        created_at="2026-01-01T00:00:00+00:00",
    )
    base.update(kwargs)
    return HandsOffSessionConfig(**base)


def test_rejects_fixed_turn_cap():
    with pytest.raises(HandsOffConfigError):
        validate_session_config(_cfg(fixed_turn_cap=10), production_mode=True)


def test_rejects_fixed_duration_cap():
    with pytest.raises(HandsOffConfigError):
        validate_session_config(_cfg(fixed_duration_cap=60.0), production_mode=True)


@pytest.mark.parametrize("field", ["scheduler_allowed", "daemon_allowed", "service_allowed", "cron_allowed"])
def test_rejects_scheduler_daemon(field):
    with pytest.raises(HandsOffConfigError):
        validate_session_config(_cfg(**{field: True}))


def test_requires_manual_stop():
    with pytest.raises(HandsOffConfigError):
        validate_session_config(_cfg(manual_stop_required=False))


def test_requires_panic():
    with pytest.raises(HandsOffConfigError):
        validate_session_config(_cfg(panic_required=False))


def test_test_harness_allows_turn_cap_in_non_production():
    cfg = validate_session_config(_cfg(fixed_turn_cap=3), production_mode=False)
    assert cfg.fixed_turn_cap == 3
