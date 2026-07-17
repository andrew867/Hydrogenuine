"""Tests for the autopilot profile selector."""

from __future__ import annotations

import pytest

from hg_runtime.profile_model_autopilot.profile_selector import (
    select_profiles_for_mode, recommended_lenses,
)


def test_selector_proposes_profiles_for_science_mode():
    r = select_profiles_for_mode("t1", "units_and_math_audit")
    assert len(r.proposed_lenses) > 0


def test_selector_pairs_falsification_with_skeptical_lens():
    r = select_profiles_for_mode("t1", "disprove_the_case")
    assert any("skeptical" in l or "falsification" in l or "debunker" in l
               for l in r.proposed_lenses)


def test_selector_pairs_public_explainer_with_public_lens():
    r = select_profiles_for_mode("t1", "public_safe_explainer")
    assert any("public" in l or "teacher" in l for l in r.proposed_lenses)


def test_selector_does_not_claim_profile_identity():
    r = select_profiles_for_mode("t1", "assume_real")
    assert r.profile_is_identity is False


def test_selector_does_not_grant_profile_authority():
    r = select_profiles_for_mode("t1", "assume_real")
    assert r.profile_grants_authority is False


def test_selector_uses_task_namespace():
    r = select_profiles_for_mode("task42", "build_the_case")
    assert "task42" in r.output_namespace


def test_selector_respects_operator_constraints():
    r = select_profiles_for_mode("t1", "disprove_the_case",
                                 operator_constraints=["debunker lens"])
    assert "debunker lens" not in r.proposed_lenses
    assert r.respects_operator_constraints is True


def test_selector_records_reason():
    r = select_profiles_for_mode("t1", "assume_false")
    assert r.reason


def test_selector_no_parallel_lifetime():
    r = select_profiles_for_mode("t1", "assume_real")
    assert r.creates_parallel_lifetime is False
    assert r.creates_persistent_memory is False


def test_recommended_lenses_for_units_audit():
    lenses = recommended_lenses("units_and_math_audit")
    assert any("physicist" in l or "proof auditor" in l for l in lenses)
