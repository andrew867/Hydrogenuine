"""Tests for cognitive profile overlay loader."""

from __future__ import annotations

import pytest


def test_loads_existing_hg_cognition_profiles():
    from hg_runtime.cognitive_profile_overlay.profile_loader import (
        load_hg_cognition_worker_profiles, hg_cognition_available,
    )
    # Either available (returns profiles) or absent (returns []), never silent fake.
    profiles = load_hg_cognition_worker_profiles()
    if hg_cognition_available():
        assert len(profiles) >= 1
    else:
        assert profiles == []


def test_validates_historical_profile():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    from hg_runtime.cognitive_profile_overlay.schemas import validate_profile_schema
    profiles = [p for p in load_all_profiles() if p.profile_kind == "historical"]
    assert len(profiles) >= 1
    ok, errors = validate_profile_schema(profiles[0])
    assert ok, errors


def test_validates_modern_profile():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    from hg_runtime.cognitive_profile_overlay.schemas import validate_profile_schema
    profiles = [p for p in load_all_profiles() if p.profile_kind == "modern"]
    assert len(profiles) >= 1
    ok, _ = validate_profile_schema(profiles[0])
    assert ok


def test_validates_fictional_profile():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    from hg_runtime.cognitive_profile_overlay.schemas import validate_profile_schema
    profiles = [p for p in load_all_profiles() if p.profile_kind == "fictional"]
    assert len(profiles) >= 1
    ok, _ = validate_profile_schema(profiles[0])
    assert ok


def test_rejects_invalid_profile_schema():
    from hg_runtime.cognitive_profile_overlay.schemas import (
        CognitiveProfile, validate_profile_schema,
    )
    bad = CognitiveProfile(
        profile_id="", profile_name="", profile_kind="not_a_kind",
        source_path="x", is_identity=True, grants_authority=True,
    )
    ok, errors = validate_profile_schema(bad)
    assert ok is False
    assert len(errors) >= 3


def test_missing_profile_is_red_or_yellow_not_silent_success():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_profile_by_id
    result = load_profile_by_id("does_not_exist_profile")
    assert result is None


def test_all_profiles_have_invariants_held():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    for p in load_all_profiles():
        assert p.is_identity is False
        assert p.grants_authority is False
        assert p.is_memory_truth is False


def test_persona_reference_data_loaded_when_present():
    from hg_runtime.cognitive_profile_overlay.persona_reference_loader import (
        persona_reference_available, load_persona_reference_profiles,
        persona_reference_counts_by_kind,
    )
    if persona_reference_available():
        profiles = load_persona_reference_profiles()
        assert len(profiles) >= 50
        counts = persona_reference_counts_by_kind()
        # culture_profiles (living/contemporary) route to "modern".
        assert counts.get("modern", 0) >= 1
        assert counts.get("historical", 0) >= 1
        assert counts.get("fictional", 0) >= 1
    else:
        assert load_persona_reference_profiles() == ()


def test_persona_reference_excludes_consciousness_markers():
    import json
    from hg_runtime.cognitive_profile_overlay.persona_reference_loader import (
        load_persona_reference_profiles, persona_reference_available,
    )
    if not persona_reference_available():
        pytest.skip("persona reference data not present")
    for p in load_persona_reference_profiles():
        blob = json.dumps(p.profile_parameters).lower()
        # A lens must never import a consciousness framing from the source data.
        assert "consciousness" not in blob
        assert "sleep_recognition" not in blob


def test_persona_living_person_profiles_are_modern_kind():
    from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
    from hg_runtime.cognitive_profile_overlay.prompt_adapter import build_profile_prompt
    modern = [p for p in load_all_profiles() if p.profile_kind == "modern"]
    if not modern:
        pytest.skip("no modern persona profiles present")
    prompt = build_profile_prompt(base_task_prompt="X", profile=modern[0], task_scope="research")
    assert "do not impersonate" in prompt.lower()
    assert "speak for any real living person" in prompt.lower()
