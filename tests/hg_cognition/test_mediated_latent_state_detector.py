from __future__ import annotations

from types import SimpleNamespace

from hg_cognition.detectors.mediated_latent_state import MediatedLatentStateDetector


def test_detector_scores_mediation_results():
    det = MediatedLatentStateDetector()
    ctx = SimpleNamespace(
        correlation_id="run-1",
        mediation_results=[
            {"mediator_id": "paired_probe", "latent_state_class": "unexpressed_disagreement", "strength": 0.7},
        ],
    )
    score = det.run([], ctx)
    assert score.name == "mediated_latent_state"
    assert score.value == 0.7
    assert score.level >= 2
