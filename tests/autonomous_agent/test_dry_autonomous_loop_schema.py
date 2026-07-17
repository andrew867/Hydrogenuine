"""Dry autonomous loop schema tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.dry_autonomous_loop.errors import DryAutonomousLoopConfigError
from hg_runtime.dry_autonomous_loop.schema import (
    FORBIDDEN_SCHEDULE_MODES,
    DryAutonomousLoopConfig,
    now_iso,
    validate_loop_config,
)


def test_config_rejects_external_side_effects():
    cfg = DryAutonomousLoopConfig(
        run_id="r1", agent_id="zero", external_side_effects_allowed=True, created_at=now_iso()
    ).with_hash()
    with pytest.raises(DryAutonomousLoopConfigError):
        validate_loop_config(cfg)


def test_config_rejects_live_writes():
    cfg = DryAutonomousLoopConfig(
        run_id="r1", agent_id="zero", live_writes_allowed=True, created_at=now_iso()
    ).with_hash()
    with pytest.raises(DryAutonomousLoopConfigError):
        validate_loop_config(cfg)


def test_config_rejects_fixture_mode():
    cfg = DryAutonomousLoopConfig(
        run_id="r1", agent_id="zero", fixture_mode_allowed=True, created_at=now_iso()
    ).with_hash()
    with pytest.raises(DryAutonomousLoopConfigError):
        validate_loop_config(cfg)


@pytest.mark.parametrize("schedule_mode", sorted(FORBIDDEN_SCHEDULE_MODES))
def test_config_rejects_forbidden_schedule_modes(schedule_mode):
    cfg = DryAutonomousLoopConfig(
        run_id="r1", agent_id="zero", schedule_mode=schedule_mode, created_at=now_iso()
    ).with_hash()
    with pytest.raises(DryAutonomousLoopConfigError, match="forbidden schedule_mode"):
        validate_loop_config(cfg)


def test_config_rejects_max_iterations_above_cap():
    cfg = DryAutonomousLoopConfig(
        run_id="r1", agent_id="zero", max_iterations=51, created_at=now_iso()
    ).with_hash()
    with pytest.raises(DryAutonomousLoopConfigError):
        validate_loop_config(cfg)


def test_config_rejects_duration_above_cap():
    cfg = DryAutonomousLoopConfig(
        run_id="r1", agent_id="zero", max_duration_seconds=7201, created_at=now_iso()
    ).with_hash()
    with pytest.raises(DryAutonomousLoopConfigError):
        validate_loop_config(cfg)


def test_config_rejects_turn_interval_below_minimum():
    cfg = DryAutonomousLoopConfig(
        run_id="r1",
        agent_id="zero",
        schedule_mode="fixed_interval",
        turn_interval_seconds=1.0,
        created_at=now_iso(),
    ).with_hash()
    with pytest.raises(DryAutonomousLoopConfigError, match="turn_interval_seconds below minimum"):
        validate_loop_config(cfg)


def test_manual_step_allows_zero_interval():
    cfg = DryAutonomousLoopConfig(
        run_id="r1",
        agent_id="zero",
        schedule_mode="manual_step",
        turn_interval_seconds=0.0,
        created_at=now_iso(),
    ).with_hash()
    out = validate_loop_config(cfg)
    assert out.hash


def test_valid_config_passes():
    cfg = DryAutonomousLoopConfig(run_id="r1", agent_id="zero", created_at=now_iso()).with_hash()
    out = validate_loop_config(cfg)
    assert out.hash
