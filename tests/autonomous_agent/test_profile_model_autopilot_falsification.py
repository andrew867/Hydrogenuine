"""Tests for falsification target extraction."""

from __future__ import annotations

import pytest

from hg_runtime.profile_model_autopilot.falsification import (
    build_falsification_targets, all_targets_have_failure_conditions,
    SPECULATIVE_PHYSICS_FAILURE_FAMILIES,
)


def _collider():
    return build_falsification_targets("collider_observer_state_coupling",
                                       "collider coupling", ["collider", "high energy"])


def test_falsification_targets_created():
    assert len(_collider()) > 0


def test_falsification_target_has_failure_condition():
    assert all_targets_have_failure_conditions(_collider())


def test_falsification_target_has_measurable_variable():
    for t in _collider():
        assert t.measurable_variable


def test_falsification_target_has_required_controls():
    primary = _collider()[0]
    assert len(primary.required_control) > 0


def test_falsification_target_records_confounders():
    primary = _collider()[0]
    assert len(primary.confounders) > 0


def test_falsification_target_records_conventional_explanation():
    primary = _collider()[0]
    assert primary.conventional_explanation


def test_speculative_physics_has_dimensional_consistency_failure_mode():
    targets = _collider()
    assert any("dimensional inconsistency" in t.failure_condition.lower() for t in targets)


def test_cern_coupling_has_scaling_failure_mode():
    targets = _collider()
    assert any("scaling" in t.failure_condition.lower() for t in targets)


def test_frequency_pattern_has_multiple_comparison_failure_mode():
    targets = build_falsification_targets("schumann_thz_mantissa_bridge",
                                          "freq", ["frequency", "schumann"])
    assert any("multiple-comparison" in t.failure_condition.lower() for t in targets)


def test_targets_not_promotable():
    for t in _collider():
        assert t.promotion_allowed is False


def test_failure_families_complete():
    assert len(SPECULATIVE_PHYSICS_FAILURE_FAMILIES) == 9
