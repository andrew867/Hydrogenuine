"""Tests for the science mode registry."""

from __future__ import annotations

import pytest

from hg_runtime.profile_model_autopilot.science_modes import (
    all_modes, get_mode, REQUIRED_MODE_IDS, any_mode_promotes_by_default,
    all_modes_require_operator_review,
)


def test_science_mode_registry_has_required_modes():
    for mid in REQUIRED_MODE_IDS:
        assert get_mode(mid) is not None


def test_build_the_case_mode_not_truth():
    m = get_mode("build_the_case")
    assert "not truth" in " ".join(m.required_boundaries)


def test_disprove_the_case_mode_not_dismissal():
    m = get_mode("disprove_the_case")
    assert "not dismissal" in " ".join(m.required_boundaries)


def test_assume_real_mode_not_fact():
    m = get_mode("assume_real")
    assert "does not promote to fact" in " ".join(m.required_boundaries)


def test_assume_false_mode_not_rejection():
    m = get_mode("assume_false")
    assert "does not prohibit future evidence" in " ".join(m.required_boundaries)


def test_boring_explanation_first_mode_exists():
    assert get_mode("boring_explanation_first") is not None


def test_units_math_audit_mode_exists():
    assert get_mode("units_and_math_audit") is not None


def test_falsification_design_mode_exists():
    assert get_mode("falsification_design") is not None


def test_synthesis_after_opposition_mode_exists():
    assert get_mode("synthesis_after_opposition") is not None


def test_every_science_mode_requires_operator_review():
    assert all_modes_require_operator_review() is True
    for m in all_modes():
        assert m.requires_operator_review is True


def test_no_science_mode_promotes_to_knowledge_by_default():
    assert any_mode_promotes_by_default() is False
    for m in all_modes():
        assert m.can_promote_to_knowledge is False


def test_twelve_modes_present():
    assert len(all_modes()) == 12
