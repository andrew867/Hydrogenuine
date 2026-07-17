"""Overnight field run schema tests."""
from __future__ import annotations

from hg_runtime.overnight_field_run.schema import FieldRunMode, OvernightFieldRunVerdict, load_field_run_policy


def test_policy_phase_24():
    policy = load_field_run_policy()
    assert policy["phase"] == 24
    assert policy["fixed_turn_cap_allowed"] is False
    assert policy["postflight_required"] is True


def test_field_run_modes():
    assert FieldRunMode.INFRASTRUCTURE_SMOKE.value == "infrastructure_smoke"
    assert FieldRunMode.OPERATOR_FIELD_RUN.value == "operator_field_run"


def test_infrastructure_verdict():
    assert "INFRASTRUCTURE_READY" in OvernightFieldRunVerdict.GREEN_INFRASTRUCTURE_READY.value
