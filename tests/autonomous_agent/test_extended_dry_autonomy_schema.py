"""Extended dry autonomy schema tests."""

from __future__ import annotations

import pytest

from hg_runtime.extended_dry_autonomy.errors import ExtendedDryAutonomyConfigError
from hg_runtime.extended_dry_autonomy.schema import ExtendedDryAutonomyConfig, now_iso, validate_config


def _cfg(**kwargs) -> ExtendedDryAutonomyConfig:
    base = dict(run_id="t", agent_id="zero", created_at=now_iso())
    base.update(kwargs)
    return ExtendedDryAutonomyConfig(**base).with_hash()


def test_rejects_external_side_effects():
    with pytest.raises(ExtendedDryAutonomyConfigError):
        validate_config(_cfg(external_side_effects_allowed=True))


def test_rejects_live_writes():
    with pytest.raises(ExtendedDryAutonomyConfigError):
        validate_config(_cfg(live_writes_allowed=True))


def test_rejects_fixture_mode():
    with pytest.raises(ExtendedDryAutonomyConfigError):
        validate_config(_cfg(fixture_mode_allowed=True))


def test_rejects_max_iterations_above_cap():
    with pytest.raises(ExtendedDryAutonomyConfigError):
        validate_config(_cfg(max_iterations=501))


def test_rejects_max_duration_above_cap():
    with pytest.raises(ExtendedDryAutonomyConfigError):
        validate_config(_cfg(max_duration_seconds=30000))


def test_rejects_small_interval():
    with pytest.raises(ExtendedDryAutonomyConfigError):
        validate_config(_cfg(turn_interval_seconds=1))
