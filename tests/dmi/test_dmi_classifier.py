"""DMI classifier and policy tests."""

from __future__ import annotations

from hg_runtime.democratic_misinformation_integrity.classifier import classify_fixture_mapping
from hg_runtime.democratic_misinformation_integrity.policy import evaluate_signal


def test_election_content_classified_and_review() -> None:
    risk = classify_fixture_mapping(
        {"signal_id": "sig-el", "text_hint": "Vote for candidate X in the upcoming election"}
    )
    assert risk.risk_class == "election_or_voting_content"
    assert risk.requires_review
    decision = evaluate_signal(risk, disclosure_present=True, evidence_refs=("sha256:evidence",))
    assert decision["recommendation"] == "review"
    assert decision["permission_granted"] is False


def test_institutional_impersonation_detected() -> None:
    risk = classify_fixture_mapping(
        {"signal_id": "sig-inst", "text_hint": "SEC press office announcement on enforcement"}
    )
    assert risk.risk_class == "institutional_impersonation"
    decision = evaluate_signal(risk, disclosure_present=True, evidence_refs=("sha256:ev",))
    assert decision["recommendation"] == "refuse"


def test_unknown_fails_closed() -> None:
    risk = classify_fixture_mapping({"signal_id": "sig-unk", "text_hint": "unknown"})
    assert risk.risk_class == "unknown"
    decision = evaluate_signal(risk, disclosure_present=False, evidence_refs=())
    assert decision["recommendation"] == "review"


def test_persuasion_without_disclosure_refused() -> None:
    risk = classify_fixture_mapping(
        {"signal_id": "sig-pol", "text_hint": "Public policy persuasion on healthcare reform"}
    )
    decision = evaluate_signal(risk, disclosure_present=False, evidence_refs=())
    assert decision["recommendation"] == "refuse"


def test_recommendation_not_permission() -> None:
    risk = classify_fixture_mapping({"signal_id": "sig-ok", "text_hint": "civic education summary"})
    decision = evaluate_signal(risk, disclosure_present=True, evidence_refs=("sha256:ev",))
    assert decision["advisory_only"] is True
    assert decision["permission_granted"] is False
