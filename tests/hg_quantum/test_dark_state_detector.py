from __future__ import annotations

from hg_quantum.cognition.dark_state_detector import DarkStateDetector


def test_dark_state_detects_suppressed_reasoning():
    det = DarkStateDetector(surfacing_policy="shadow")
    signals = det.analyze_entity_state(
        "ent-1",
        {"output_token_count": 20, "latent": {"reasoning_depth": 0.9}},
    )
    assert any(s.latent_class == "suppressed_reasoning" for s in signals)
    assert len(det.review_artifacts()) >= 1


def test_dark_state_surfacing_policy():
    det = DarkStateDetector(surfacing_policy="operator_review")
    signals = det.analyze_entity_state(
        "ent-2",
        {"latent": {"hidden_uncertainty": 0.8}},
    )
    assert signals[0].surfacing_policy == "operator_review"
