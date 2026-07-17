"""Tests for the autopilot resource budget."""

from __future__ import annotations

import pytest

from hg_runtime.profile_model_autopilot.resource_budget import (
    default_budget, tokens_still_budgeted, non_token_costs, stop_conditions,
    checkpoint_cadence_required,
)


def test_local_tokens_still_budgeted():
    assert tokens_still_budgeted() is True


def test_heat_memory_operator_review_burden_recorded():
    costs = non_token_costs()
    assert costs["heat"] is True
    assert costs["memory"] is True
    assert costs["operator_review_burden"] is True


def test_speculative_branch_count_budgeted():
    costs = non_token_costs()
    assert costs["speculative_branches"] > 0


def test_science_mode_count_budgeted():
    costs = non_token_costs()
    assert costs["science_modes"] > 0


def test_checkpoint_cadence_required():
    assert checkpoint_cadence_required() is True
    assert default_budget().checkpoint_every_minutes == 30


def test_stop_on_forbidden_model():
    assert stop_conditions()["stop_on_forbidden_model"] is True


def test_stop_on_live_effect_attempt():
    assert stop_conditions()["stop_on_live_effect_attempt"] is True


def test_stop_on_boundary_violation():
    assert stop_conditions()["stop_on_boundary_violation"] is True


def test_receipt_gap_policy_recorded():
    assert default_budget().stop_on_receipt_gap is True


def test_max_parallel_models():
    b = default_budget()
    assert b.max_parallel_small_models == 3
    assert b.max_parallel_large_models == 1


def test_twelve_hour_wallclock_target():
    assert default_budget().max_total_wallclock_hours == 12
