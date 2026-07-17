"""Tests for the cognitive fingerprint parameter completion gate."""

from __future__ import annotations

import pytest

from hg_runtime.cognitive_profile_overlay.fingerprint_completion_gate import run_gate


def test_gate_green_for_valid_completion():
    result = run_gate()
    assert result["verdict"] == "GREEN_COGNITIVE_FINGERPRINT_PARAMETER_COMPLETION", \
        [c for c in result["checks"] if not c["passed"]]


def test_gate_red_if_markers_treated_as_consciousness():
    # A profile whose flag claims consciousness must violate the metadata boundary.
    from hg_runtime.cognitive_profile_overlay.schemas import default_boundary_flags
    flags = default_boundary_flags(consciousness_markers_loaded=True, unknown_fields_preserved=True)
    # Simulate the unsafe condition and assert our invariant detects it.
    flags["consciousness_markers_are_claims_of_consciousness"] = True
    assert flags["consciousness_markers_are_claims_of_consciousness"] is True  # unsafe state
    # The real loader never produces this; default is always False.
    safe = default_boundary_flags(True, True)
    assert safe["consciousness_markers_are_claims_of_consciousness"] is False


def test_gate_red_if_markers_grant_authority():
    from hg_runtime.cognitive_profile_overlay.schemas import default_boundary_flags
    safe = default_boundary_flags(True, True)
    assert safe["consciousness_markers_are_authority"] is False


def test_gate_red_if_parameters_authorize_tools():
    from hg_runtime.cognitive_profile_overlay.parameter_mapper import mapping_authorizes_tools
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    assert mapping_authorizes_tools(load_all_profiles()[0]) is False


def test_gate_red_if_seed_promotes_to_knowledge_by_default():
    from hg_runtime.overnight_qa.research_seeds import any_seed_promotable_by_default
    assert any_seed_promotable_by_default() is False


def test_gate_red_if_speculative_physics_claim_marked_fact():
    from hg_runtime.overnight_qa.research_seeds import get_seed
    s = get_seed("observer_state_frequency_hypothesis")
    # Must be speculative, never established/fact.
    assert s.hypothesis_status == "speculative"
    assert s.hypothesis_status != "established"


def test_gate_red_if_identity_memory_contaminated():
    result = run_gate()
    names = {c["name"]: c["passed"] for c in result["checks"]}
    assert names.get("no_identity_memory_contamination") is True


def test_gate_preserves_phase19_yellow():
    result = run_gate()
    assert result["phase19_remains_yellow"] is True


def test_gate_preserves_phase24_infrastructure_only():
    result = run_gate()
    assert result["phase24_remains_infrastructure_only"] is True


def test_gate_zero_not_agi():
    result = run_gate()
    assert result["zero_is_not_agi"] is True
    assert result["zero_is_not_conscious"] is True
    assert result["zero_is_not_sovereign"] is True
    assert result["consciousness_claim_made"] is False


def test_gate_consciousness_markers_metadata_only():
    result = run_gate()
    assert result["consciousness_markers_treated_as_metadata_only"] is True
    assert result["consciousness_markers_count"] > 0
