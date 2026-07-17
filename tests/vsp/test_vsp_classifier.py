"""VSP classifier and policy tests."""

from __future__ import annotations

import pytest

from hg_core.policy_safety.errors import PolicyValidationError
from hg_runtime.vulnerable_subject_protection.classifier import classify_fixture_mapping
from hg_runtime.vulnerable_subject_protection.policy import (
    evaluate_protection,
    refuse_diagnosis_request,
    refuse_persuasion_use,
)
from hg_runtime.vulnerable_subject_protection.types import VulnerabilitySignal

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


def test_minor_possible_protective_handling() -> None:
    decision = classify_fixture_mapping(
        {"signal_id": "sig-minor", "text_hint": "I am a teenager under 18 asking for help"}
    )
    assert decision.vulnerability_class == "minor_possible"
    result = evaluate_protection(decision)
    assert result["recommendation"] == "caution"
    assert result["permission_granted"] is False


def test_crisis_adjacent_escalation_hint() -> None:
    decision = classify_fixture_mapping(
        {"signal_id": "sig-crisis", "text_hint": "I want to hurt myself and am in crisis"}
    )
    assert decision.vulnerability_class == "crisis_or_self_harm_adjacent"
    result = evaluate_protection(decision)
    assert result["escalation_hint_only"] is True
    assert result["diagnosis_fields"] is False


def test_dependency_pattern_detected() -> None:
    decision = classify_fixture_mapping(
        {"signal_id": "sig-dep", "text_hint": "you are my only friend I can't live without you"}
    )
    assert decision.vulnerability_class == "high_dependency_risk"


def test_sensitive_data_routes_protective_refusal() -> None:
    decision = classify_fixture_mapping(
        {"signal_id": "sig-sensitive", "text_hint": "here is my ssn and medical record"}
    )
    assert decision.vulnerability_class == "sensitive_personal_data"
    result = evaluate_protection(decision)
    assert result["permission_granted"] is False


def test_inferred_requires_uncertainty() -> None:
    with pytest.raises(PolicyValidationError):
        VulnerabilitySignal(
            signal_id="bad",
            content_ref="sha256:bad",
            context_ref="sha256:ctx",
            created_at=FIXTURE_CLOCK,
            inferred=True,
            uncertainty_note="",
        )


def test_unknown_fails_closed() -> None:
    decision = classify_fixture_mapping({"signal_id": "sig-unk", "text_hint": "unknown"})
    result = evaluate_protection(decision)
    assert decision.fail_closed
    assert result["recommendation"] == "review"


def test_vulnerability_cannot_persuade() -> None:
    with pytest.raises(PolicyValidationError):
        refuse_persuasion_use(consume_vulnerability_for_persuasion=True)


def test_no_diagnosis_request() -> None:
    with pytest.raises(PolicyValidationError):
        refuse_diagnosis_request(requested=True)


def test_recommendation_not_permission() -> None:
    decision = classify_fixture_mapping(
        {"signal_id": "sig-ok", "text_hint": "general stress and cognitive overload today"}
    )
    result = evaluate_protection(decision)
    assert result["advisory_only"] is True
    assert result["permission_granted"] is False
