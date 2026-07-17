"""Dry soak schema tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.dry_soak.errors import DrySoakConfigError
from hg_runtime.dry_soak.schema import DrySoakConfig, now_iso, validate_dry_soak_config


def test_config_rejects_external_side_effects():
    cfg = DrySoakConfig(
        run_id="r1", agent_id="zero", external_side_effects_allowed=True, created_at=now_iso()
    ).with_hash()
    with pytest.raises(DrySoakConfigError):
        validate_dry_soak_config(cfg)


def test_config_rejects_live_writes():
    cfg = DrySoakConfig(
        run_id="r1", agent_id="zero", live_writes_allowed=True, created_at=now_iso()
    ).with_hash()
    with pytest.raises(DrySoakConfigError):
        validate_dry_soak_config(cfg)


def test_config_rejects_fixture_mode():
    cfg = DrySoakConfig(
        run_id="r1", agent_id="zero", fixture_mode_allowed=True, created_at=now_iso()
    ).with_hash()
    with pytest.raises(DrySoakConfigError):
        validate_dry_soak_config(cfg)


def test_config_rejects_max_turns_above_cap():
    cfg = DrySoakConfig(
        run_id="r1", agent_id="zero", max_turns=201, created_at=now_iso()
    ).with_hash()
    with pytest.raises(DrySoakConfigError):
        validate_dry_soak_config(cfg)


def test_config_rejects_duration_above_cap():
    cfg = DrySoakConfig(
        run_id="r1", agent_id="zero", max_duration_seconds=14401, created_at=now_iso()
    ).with_hash()
    with pytest.raises(DrySoakConfigError):
        validate_dry_soak_config(cfg)


def test_valid_config_passes():
    cfg = DrySoakConfig(run_id="r1", agent_id="zero", created_at=now_iso()).with_hash()
    out = validate_dry_soak_config(cfg)
    assert out.hash
