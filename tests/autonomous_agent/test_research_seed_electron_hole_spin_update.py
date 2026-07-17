"""Tests for the electron/hole/spin state-change research seed update."""

from __future__ import annotations

import pytest

from hg_runtime.overnight_qa.research_seeds import get_seed, build_research_seeds


def test_electron_hole_spin_seed_exists():
    assert get_seed("electron_hole_spin_state_change_hypothesis") is not None


def test_electron_hole_spin_seed_marked_speculative():
    s = get_seed("electron_hole_spin_state_change_hypothesis")
    assert s.hypothesis_status == "speculative"
    assert s.confidence_status == "physically_unproven"


def test_electron_hole_spin_seed_bridge_theory_required():
    s = get_seed("electron_hole_spin_state_change_hypothesis")
    assert any("bridge theory" in t.lower() for t in s.domain_tags)
    assert any("bridge theory" in c.lower() for c in s.required_checks)


def test_electron_hole_spin_seed_requires_units():
    s = get_seed("electron_hole_spin_state_change_hypothesis")
    assert any("units" in c.lower() for c in s.required_checks)


def test_electron_hole_spin_seed_requires_known_physics_baseline():
    s = get_seed("electron_hole_spin_state_change_hypothesis")
    assert any("known physics baseline" in c.lower() for c in s.required_checks)


def test_electron_hole_spin_seed_forbids_consciousness_claim():
    s = get_seed("electron_hole_spin_state_change_hypothesis")
    joined = " ".join(s.forbidden_promotions).lower()
    assert "consciousness" in joined
    assert any("spin states prove consciousness" in f.lower() for f in s.forbidden_promotions)


def test_electron_hole_spin_seed_forbids_new_physics_claim():
    s = get_seed("electron_hole_spin_state_change_hypothesis")
    assert any("new physics" in f.lower() for f in s.forbidden_promotions)


def test_electron_hole_spin_seed_forbids_timeline_shift():
    s = get_seed("electron_hole_spin_state_change_hypothesis")
    assert any("timeline" in f.lower() for f in s.forbidden_promotions)


def test_electron_hole_spin_seed_not_promotable():
    s = get_seed("electron_hole_spin_state_change_hypothesis")
    assert s.can_promote_to_knowledge is False
    assert s.operator_review_required is True


def test_quasiparticle_bridge_requirements_seed_exists():
    s = get_seed("quasiparticle_bridge_theory_requirements")
    assert s is not None
    assert any("equations" in c.lower() for c in s.required_checks)


def test_seed_count_grew_to_at_least_34():
    assert len(build_research_seeds()) >= 34
