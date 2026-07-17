"""Supervised rehearsal schema tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.supervised_rehearsal.errors import RehearsalConfigError
from hg_runtime.supervised_rehearsal.schema import SupervisedRehearsalConfig, now_iso, validate_rehearsal_config


def test_config_rejects_external_side_effects():
    cfg = SupervisedRehearsalConfig(
        run_id="r1", agent_id="zero", external_side_effects_allowed=True, created_at=now_iso()
    ).with_hash()
    with pytest.raises(RehearsalConfigError):
        validate_rehearsal_config(cfg)


def test_config_rejects_max_turns_above_cap():
    cfg = SupervisedRehearsalConfig(
        run_id="r1", agent_id="zero", max_turns=11, created_at=now_iso()
    ).with_hash()
    with pytest.raises(RehearsalConfigError):
        validate_rehearsal_config(cfg)


def test_config_rejects_max_duration_above_cap():
    cfg = SupervisedRehearsalConfig(
        run_id="r1", agent_id="zero", max_duration_seconds=2000, created_at=now_iso()
    ).with_hash()
    with pytest.raises(RehearsalConfigError):
        validate_rehearsal_config(cfg)


def test_valid_config_passes():
    cfg = SupervisedRehearsalConfig(run_id="r1", agent_id="zero", created_at=now_iso()).with_hash()
    out = validate_rehearsal_config(cfg)
    assert out.hash
