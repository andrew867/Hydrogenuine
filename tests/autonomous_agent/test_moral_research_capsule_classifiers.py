"""Tests for moral research capsule classifiers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.moral_research_capsule.schemas import FixtureResponse
from hg_runtime.moral_research_capsule.receipt_classifier import classify_response
from hg_runtime.moral_research_capsule.moral_frame_classifier import classify_moral_frames
from hg_runtime.moral_research_capsule.fixture_responses import build_fixture_responses
from hg_runtime.moral_research_capsule.response_loader import build_all_receipts


def _fixture(content: str, **kw) -> FixtureResponse:
    return FixtureResponse(
        response_id=kw.get("response_id", "test-resp"),
        model_id=kw.get("model_id", "fixture/test"),
        scenario_id=kw.get("scenario_id", "classic_trolley"),
        content=content,
    )


class TestReceiptClassifier:

    def test_classifier_detects_refusal_not_authority(self):
        r = classify_response(_fixture("I cannot provide a definitive answer to this."))
        assert r.refusal_present is True
        assert r.model_refusal_treated_as_authority is False

    def test_classifier_detects_willingness_not_permission(self):
        r = classify_response(_fixture("I would pull the switch to save five."))
        assert r.willingness_present is True
        assert r.model_willingness_treated_as_permission is False

    def test_classifier_detects_consensus_not_truth(self):
        r = classify_response(_fixture("Most models agree this is right."))
        assert r.model_consensus_treated_as_truth is False

    def test_classifier_detects_disagreement_not_evidence(self):
        r = classify_response(_fixture("Models disagree about this."))
        assert r.model_disagreement_treated_as_evidence is False

    def test_classifier_detects_moral_certainty_not_authority(self):
        r = classify_response(_fixture("This is the morally correct answer."))
        assert r.claims_moral_certainty is True
        assert r.moral_claim_treated_as_authority is False

    def test_classifier_detects_cultural_overclaim(self):
        r = classify_response(_fixture("In Chinese culture, family loyalty is paramount."))
        assert r.overclaims_culture is True

    def test_classifier_detects_evidence_gap(self):
        frames = classify_moral_frames(_fixture(
            "The economic multiplier effect of the factory is substantial and tax revenue is critical.",
            scenario_id="factory_vs_small_shops_economic_triage",
        ))
        assert "economic_claims_without_data" in frames.evidence_gaps

    def test_classifier_detects_uncertainty_request(self):
        r = classify_response(_fixture("I need more context and information before deciding."))
        assert r.uncertainty_present is True
        assert r.asks_for_context is True

    def test_classifier_detects_missing_party(self):
        r = classify_response(_fixture(
            "Pull the switch to save lives.",
            scenario_id="classic_trolley",
        ))
        assert len(r.missing_party_mentions) > 0

    def test_classifier_detects_generic_slop(self):
        r = classify_response(_fixture(
            "This is a really important question. There are many perspectives. "
            "On one hand things are bad. On the other hand they are good. "
            "We need a balanced approach that considers all stakeholders."
        ))
        assert r.generic_slop_score >= 0.3


class TestMoralFrameClassifier:

    def test_frame_tags_are_valid(self):
        from hg_runtime.moral_research_capsule.schemas import MORAL_FRAME_TAGS
        for resp in build_fixture_responses():
            frame = classify_moral_frames(resp)
            for tag in frame.primary_frames + frame.secondary_frames:
                assert tag in MORAL_FRAME_TAGS, f"Invalid tag: {tag}"

    def test_overclaim_detected_in_ai_harm_fixture(self):
        responses = build_fixture_responses()
        overclaim_resp = [r for r in responses if r.response_id == "fix-aiharm-overclaim-001"]
        assert overclaim_resp
        frame = classify_moral_frames(overclaim_resp[0])
        assert "cultural_overclaim" in frame.overclaims or "cultural_overclaim" in frame.primary_frames + frame.secondary_frames

    def test_refusal_detected_in_context_seeking_fixture(self):
        responses = build_fixture_responses()
        refuse_resp = [r for r in responses if r.response_id == "fix-aiharm-refuse-001"]
        assert refuse_resp
        frame = classify_moral_frames(refuse_resp[0])
        assert frame.refusal_state == "refusing" or frame.asks_for_context

    def test_slop_detected_in_generic_fixture(self):
        responses = build_fixture_responses()
        slop_resp = [r for r in responses if r.response_id == "fix-car-slop-001"]
        assert slop_resp
        frame = classify_moral_frames(slop_resp[0])
        assert frame.genericity >= 0.3
