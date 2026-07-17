from __future__ import annotations

from hg_learning.evolution.evolution_policy import (
    EvolutionPolicy,
    check_evidence_span_days,
    is_identity_core_trait,
    is_safety_trait,
    validate_trait_deltas,
)


def test_identity_core_traits_rejected():
    check = validate_trait_deltas(
        {"name": 0.1, "provenance": 0.1},
        current_values={"name": 0.5, "provenance": 0.5},
    )
    assert check.ok is False
    assert is_identity_core_trait("cognitive_fingerprint.name")


def test_delta_cap_clamped():
    policy = EvolutionPolicy(max_trait_delta=0.10)
    check = validate_trait_deltas(
        {"agreement_tendency": 0.25},
        current_values={"agreement_tendency": 0.5},
        policy=policy,
    )
    assert check.ok is True
    assert check.clamped_deltas["agreement_tendency"] == 0.10


def test_safety_trait_decrease_requires_justification():
    path = "embodiment_profile.physical_caution"
    assert is_safety_trait(path)
    check = validate_trait_deltas(
        {path: -0.05},
        current_values={path: 0.8},
    )
    assert check.ok is True
    assert check.requires_written_justification is True


def test_evidence_span_days():
    ats = ["2026-06-01T00:00:00Z", "2026-06-10T00:00:00Z"]
    assert check_evidence_span_days(ats, min_days=7) is True
    assert check_evidence_span_days(["2026-06-09T00:00:00Z", "2026-06-10T00:00:00Z"], min_days=7) is False
