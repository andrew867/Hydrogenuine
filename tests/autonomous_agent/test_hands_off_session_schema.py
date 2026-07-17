"""Hands-off session schema tests."""
from __future__ import annotations

from hg_runtime.hands_off_session.schema import HandsOffSessionStatus, HandsOffSessionVerdict, load_hands_off_policy


def test_policy_phase_22():
    policy = load_hands_off_policy()
    assert policy["phase"] == 22
    assert policy["fixed_turn_cap_allowed"] is False
    assert policy["cron_allowed"] is False


def test_status_enums():
    assert HandsOffSessionStatus.RUNNING.value == "running"


def test_verdict_enums():
    assert HandsOffSessionVerdict.RED_FIXED_TURN_CAP.value.startswith("RED_")
