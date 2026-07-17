"""Tests for the paced long-run loop launcher policy."""

from __future__ import annotations

import pytest

from hg_runtime.live_local.paced_loop import (
    parse_args, overnight_green_allowed, verdict_for_run, due_checkins, PacedLoopConfig,
)


def test_paced_loop_requires_real_duration_for_green():
    # 13 minutes of a 12h target cannot be GREEN-as-overnight.
    assert overnight_green_allowed(target_seconds=12 * 3600, elapsed_seconds=13 * 60) is False


def test_compressed_run_cannot_be_green_overnight():
    v = verdict_for_run(target_seconds=12 * 3600, elapsed_seconds=13 * 60)
    assert v == "YELLOW_OVERNIGHT_BOUNDED_FULL_SEND_PARTIAL"


def test_full_duration_meeting_minimum_can_be_green():
    v = verdict_for_run(target_seconds=12 * 3600, elapsed_seconds=12 * 3600 + 5)
    assert v == "GREEN_OVERNIGHT_BOUNDED_FULL_SEND_SOAK"


def test_short_target_below_minimum_not_green():
    # Even if a 20-min target is reached, it is below the 4h overnight minimum.
    assert overnight_green_allowed(target_seconds=20 * 60, elapsed_seconds=21 * 60) is False


def test_hourly_checkins_written_by_wallclock():
    assert due_checkins(0, 60) == 1            # hour_00
    assert due_checkins(3 * 3600, 60) == 4     # hour_00..03
    assert due_checkins(59 * 60, 60) == 1      # still hour_00 before 1h


def test_partial_stop_writes_yellow():
    v = verdict_for_run(target_seconds=4 * 3600, elapsed_seconds=600, operator_stop=True)
    assert v == "YELLOW_OVERNIGHT_BOUNDED_FULL_SEND_PARTIAL"


def test_stop_panic_honored():
    assert overnight_green_allowed(target_seconds=3600, elapsed_seconds=3601, panic=True) is False


def test_boundary_violation_is_red():
    v = verdict_for_run(target_seconds=3600, elapsed_seconds=3601, boundaries_held=False)
    assert v == "RED_OVERNIGHT_BOUNDED_FULL_SEND_FAILED"


def test_per_call_timeout_configurable():
    cfg = parse_args(["--duration-hours", "12", "--per-call-timeout-seconds", "300"])
    assert cfg.per_call_timeout_seconds == 300
    assert cfg.target_seconds() == 12 * 3600


def test_final_answer_retry_enabled():
    cfg = parse_args(["--duration-minutes", "20", "--final-answer-retry"])
    assert cfg.final_answer_retry is True
    assert cfg.target_seconds() == 20 * 60


def test_browsing_disabled_default():
    cfg = parse_args(["--duration-hours", "12"])
    assert cfg.browsing == "disabled"
