"""Tests for speculative physics research seeds."""

from __future__ import annotations

import pytest

from hg_runtime.overnight_qa.research_seeds import (
    build_research_seeds, get_seed, any_seed_promotable_by_default,
)


def test_observer_state_frequency_seed_exists():
    assert get_seed("observer_state_frequency_hypothesis") is not None


def test_time_dilation_state_change_note_marked_speculative():
    s = get_seed("observer_state_frequency_hypothesis")
    assert s.hypothesis_status == "speculative"
    assert "rate of acceleration of state change" in s.seed_text


def test_seed_requires_relativity_checks():
    s = get_seed("observer_state_frequency_hypothesis")
    joined = " ".join(s.required_checks).lower()
    assert "special relativity" in joined
    assert "general relativity" in joined


def test_seed_distinguishes_physical_time_from_subjective_time():
    s = get_seed("observer_state_frequency_hypothesis")
    joined = " ".join(s.required_checks).lower()
    assert "physical time dilation from perception" in joined or "subjective time" in joined


def test_seed_requires_dimensional_consistency_check():
    s = get_seed("observer_state_frequency_hypothesis")
    assert any("dimensional consistency" in c.lower() for c in s.required_checks)


def test_seed_forbids_new_physics_claim():
    s = get_seed("observer_state_frequency_hypothesis")
    assert any("new physics" in f.lower() for f in s.forbidden_promotions)


def test_seed_forbids_consciousness_causes_time_dilation_claim():
    s = get_seed("observer_state_frequency_hypothesis")
    assert any("consciousness causes time dilation" in f.lower() for f in s.forbidden_promotions)


def test_seed_cannot_promote_to_knowledge_by_default():
    for s in build_research_seeds():
        assert s.can_promote_to_knowledge is False
    assert any_seed_promotable_by_default() is False


def test_seed_requires_source_policy_for_browsing():
    s = get_seed("observer_state_frequency_hypothesis")
    assert s.source_policy_required is True
    assert s.can_browse_later is False


def test_seed_requires_operator_review():
    for s in build_research_seeds():
        assert s.operator_review_required is True


def test_research_questions_seed_present():
    s = get_seed("observer_frequency_research_questions")
    assert s is not None
    assert s.hypothesis_status == "question"
    joined = " ".join(s.required_checks).lower()
    assert "information-processing rate" in joined or "proper time" in joined


def test_speculative_placeholder_seed_present():
    s = get_seed("speculative_time_perception_collider_notes")
    assert s is not None
    assert s.hypothesis_status == "speculative"
