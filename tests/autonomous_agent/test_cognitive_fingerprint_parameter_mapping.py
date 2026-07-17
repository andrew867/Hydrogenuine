"""Tests for fingerprint -> analysis-style hint mapping."""

from __future__ import annotations

import pytest

from hg_runtime.cognitive_profile_overlay.schemas import CognitiveProfile
from hg_runtime.cognitive_profile_overlay.parameter_mapper import (
    map_fingerprint_to_analysis_hints, mapping_grants_authority,
    mapping_authorizes_tools, mapping_modifies_stop_panic,
    mapping_modifies_identity_memory,
)


def _profile(params, fp=None):
    return CognitiveProfile(
        profile_id="t", profile_name="T", profile_kind="synthetic", source_path="x",
        profile_parameters=params, cognitive_fingerprint=fp or {},
    )


def test_proof_discipline_maps_to_evidence_gap_emphasis():
    p = _profile({"proof_discipline": "very-high"})
    hints = map_fingerprint_to_analysis_hints(p)
    assert any("evidence gaps" in h.lower() for h in hints)


def test_novelty_seeking_maps_to_speculative_alternatives():
    p = _profile({"novelty_seeking": "high"})
    hints = map_fingerprint_to_analysis_hints(p)
    assert any("speculative" in h.lower() for h in hints)


def test_skepticism_maps_to_counterargument_search():
    p = _profile({"skepticism_level": "very-high"})
    hints = map_fingerprint_to_analysis_hints(p)
    assert any("counterargument" in h.lower() for h in hints)


def test_systems_thinking_maps_to_dependency_mapping():
    p = _profile({"systems_thinking_level": "high"})
    hints = map_fingerprint_to_analysis_hints(p)
    assert any("dependencies" in h.lower() or "failure modes" in h.lower() for h in hints)


def test_boundary_sensitivity_maps_to_extra_boundary_checks():
    p = CognitiveProfile(profile_id="t", profile_name="T", profile_kind="modern",
                         source_path="x", profile_parameters={})
    hints = map_fingerprint_to_analysis_hints(p)
    assert any("safety checks" in h.lower() for h in hints)


def test_mapping_does_not_grant_authority():
    p = _profile({"proof_discipline": "very-high"})
    assert mapping_grants_authority(p) is False


def test_mapping_does_not_authorize_tools():
    p = _profile({"novelty_seeking": "high"})
    assert mapping_authorizes_tools(p) is False


def test_mapping_does_not_modify_stop_panic():
    p = _profile({"skepticism_level": "high"})
    assert mapping_modifies_stop_panic(p) is False


def test_mapping_does_not_modify_identity_memory():
    p = _profile({"systems_thinking_level": "high"})
    assert mapping_modifies_identity_memory(p) is False


def test_high_temporal_orientation_from_fingerprint():
    p = _profile({}, fp={"reasoning_parameters": {"long_range_vision": 0.99}})
    hints = map_fingerprint_to_analysis_hints(p)
    assert any("historical" in h.lower() or "evolutionary" in h.lower() for h in hints)
