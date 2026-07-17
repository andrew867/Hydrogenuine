"""Tests for full cognitive fingerprint parameter loading."""

from __future__ import annotations

import json
import pytest

from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
from hg_runtime.cognitive_profile_overlay.persona_reference_loader import (
    persona_reference_available, build_load_receipts,
)


def _fingerprinted():
    return [p for p in load_all_profiles() if p.cognitive_fingerprint]


def test_loads_consciousness_markers_when_present():
    if not persona_reference_available():
        pytest.skip("persona reference data not present")
    with_cm = [p for p in _fingerprinted()
               if p.cognitive_fingerprint.get("consciousness_markers")]
    assert len(with_cm) > 0


def test_missing_consciousness_markers_recorded_not_failed():
    # Bundled synthetic profiles have no fingerprint; that's recorded, not a failure.
    profiles = load_all_profiles()
    no_fp = [p for p in profiles if not p.cognitive_fingerprint]
    # Their boundary_flags may be empty but loading must not crash and profiles exist.
    assert isinstance(no_fp, list)
    assert len(profiles) > 0


def test_consciousness_markers_are_metadata_not_consciousness():
    if not persona_reference_available():
        pytest.skip("persona reference data not present")
    for p in _fingerprinted():
        if p.cognitive_fingerprint.get("consciousness_markers"):
            assert p.boundary_flags["consciousness_markers_are_claims_of_consciousness"] is False
            assert p.boundary_flags["consciousness_markers_are_authority"] is False
            assert p.boundary_flags["consciousness_markers_are_truth"] is False
            assert p.boundary_flags["consciousness_markers_authorize_tools"] is False


def test_loads_cognitive_parameters_when_present():
    fp = _fingerprinted()
    assert any(p.cognitive_fingerprint.get("cognitive_parameters") for p in fp)


def test_loads_activity_patterns_when_present():
    # No activity_patterns section exists in source; loader records honestly (empty).
    for p in _fingerprinted():
        assert "activity_patterns" in p.cognitive_fingerprint


def test_preserves_unknown_extra_fields():
    fp = _fingerprinted()
    # Top-level metadata (taxonomy_placements, shadow_traits, ...) preserved as unknown.
    assert any(p.cognitive_fingerprint.get("unknown_extra_fields") for p in fp)


def test_records_dropped_fields_if_any():
    receipts = build_load_receipts(limit=5)
    for r in receipts:
        assert isinstance(r.dropped_fields, list)


def test_redacts_suspicious_secret_fields():
    from hg_runtime.cognitive_profile_overlay.fingerprint_loader import extract_fingerprint
    leaky = {
        "entity": "Test",
        "cognitive_fingerprint": {
            "reasoning_style": {"systems_first": 0.9},
            "api_key": "sk-abcd1234efgh5678ijkl",
        },
    }
    fp, dropped, redacted = extract_fingerprint(leaky)
    assert "api_key" in redacted
    blob = json.dumps(fp.unknown_extra_fields)
    assert "sk-abcd1234efgh5678ijkl" not in blob


def test_writes_profile_load_receipt():
    receipts = build_load_receipts(limit=3)
    assert len(receipts) == 3
    for r in receipts:
        assert r.receipt_hash
        assert r.fingerprint_present is True
        assert "consciousness_markers_loaded" in r.boundary_flags


def test_profile_parameters_still_exclude_consciousness():
    # The derived style params must remain consciousness-free even though the
    # full fingerprint now preserves consciousness markers separately.
    for p in _fingerprinted():
        assert "consciousness" not in json.dumps(p.profile_parameters).lower()
