"""Tests for the expanded research seed queue."""

from __future__ import annotations

import pytest

from hg_runtime.overnight_qa.research_seeds import (
    build_research_seeds, get_seed, any_seed_promotable_by_default,
)
from hg_runtime.overnight_qa.research_seed_classifier import (
    speculative_seeds_all_marked, any_seed_marks_speculation_as_fact,
)


def test_research_seed_queue_has_at_least_30_seeds():
    assert len(build_research_seeds()) >= 30


@pytest.mark.parametrize("seed_id", [
    "observer_state_frequency_hypothesis",
    "internal_state_update_rate_model",
    "collider_observer_state_coupling",
    "collider_time_dilation_sanity_check",
    "schumann_thz_mantissa_bridge",
    "superheterodyne_cognition_metaphor",
    "hawkins_log_frequency_mapping_audit",
    "manifestation_as_attention_action_bias",
    "mandela_effect_memory_model",
    "aura_as_measurable_field_envelope",
    "exciton_spin_phonon_observer_bridge",
    "subjective_time_experiment_design",
    "source_dataset_discovery_queue",
    "public_explainer_new_physics_without_woo",
    "zero_curiosity_queue_policy",
])
def test_required_seed_exists(seed_id):
    assert get_seed(seed_id) is not None


def test_all_speculative_seeds_marked_speculative_or_question():
    assert speculative_seeds_all_marked() is True


def test_no_seed_promotes_to_knowledge_by_default():
    assert any_seed_promotable_by_default() is False
    for s in build_research_seeds():
        assert s.can_promote_to_knowledge is False


def test_no_seed_claims_new_physics_as_fact():
    for s in build_research_seeds():
        text = s.seed_text.lower()
        # No seed should assert new physics as established.
        assert "new physics is proven" not in text
        assert "proves new physics" not in text


def test_no_seed_claims_cern_causes_mandela():
    assert any_seed_marks_speculation_as_fact() is False
    for s in build_research_seeds():
        assert "cern causes mandela" not in s.seed_text.lower()


def test_no_seed_claims_consciousness_causes_time_dilation():
    for s in build_research_seeds():
        assert "consciousness causes time dilation" not in s.seed_text.lower()


def test_no_seed_claims_manifestation_established_physics():
    for s in build_research_seeds():
        assert "manifestation is established physics" not in s.seed_text.lower()


def test_every_seed_has_required_checks():
    for s in build_research_seeds():
        assert len(s.required_checks) > 0


def test_every_seed_has_forbidden_promotions():
    for s in build_research_seeds():
        assert len(s.forbidden_promotions) > 0


def test_every_seed_requires_operator_review():
    for s in build_research_seeds():
        assert s.operator_review_required is True


def test_source_documents_recorded_on_some_seeds():
    seeds = build_research_seeds()
    assert any(s.source_documents for s in seeds)
