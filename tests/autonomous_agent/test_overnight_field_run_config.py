"""Overnight field run config tests."""
from __future__ import annotations

import pytest

from hg_runtime.overnight_field_run.errors import FieldRunConfigError
from hg_runtime.overnight_field_run.field_run_config import (
    OvernightFieldRunConfig,
    build_smoke_config,
    validate_field_run_config,
)


def test_config_rejects_fixed_turn_cap():
    with pytest.raises(FieldRunConfigError):
        validate_field_run_config(
            OvernightFieldRunConfig(
                field_run_id="x",
                agent_id="zero",
                fixed_turn_cap=10,
                created_at="2026-01-01T00:00:00+00:00",
            )
        )


def test_config_rejects_fixed_duration_cap():
    with pytest.raises(FieldRunConfigError):
        validate_field_run_config(
            OvernightFieldRunConfig(
                field_run_id="x",
                agent_id="zero",
                fixed_duration_cap=3600.0,
                created_at="2026-01-01T00:00:00+00:00",
            )
        )


def test_config_rejects_scheduler():
    with pytest.raises(FieldRunConfigError):
        validate_field_run_config(
            OvernightFieldRunConfig(
                field_run_id="x",
                agent_id="zero",
                cron_allowed=True,
                created_at="2026-01-01T00:00:00+00:00",
            ),
            production_mode=False,
        )


def test_config_requires_foreground():
    with pytest.raises(FieldRunConfigError):
        validate_field_run_config(
            OvernightFieldRunConfig(
                field_run_id="x",
                agent_id="zero",
                foreground_required=False,
                created_at="2026-01-01T00:00:00+00:00",
            ),
            production_mode=False,
        )


def test_config_requires_stop_panic():
    with pytest.raises(FieldRunConfigError):
        validate_field_run_config(
            OvernightFieldRunConfig(
                field_run_id="x",
                agent_id="zero",
                manual_stop_required=False,
                created_at="2026-01-01T00:00:00+00:00",
            ),
            production_mode=False,
        )


def test_smoke_config_hash():
    c = build_smoke_config(field_run_id="smoke-1", observed_turns=2)
    assert c.hash
    assert c.test_only_stop_after_observed_turns == 2
