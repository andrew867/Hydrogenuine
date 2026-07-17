"""Quantum detector registration via shared registry."""
from __future__ import annotations

import pytest

from hg_cognition.detectors.registry import build_standard_detectors
from hg_cognition.detectors.quantum_noise import QuantumNoiseDetector
from hg_cognition.detectors.entanglement_anomaly import EntanglementAnomalyDetector
from hg_cognition.schemas.trace import StepTrace
from hg_cognition.detectors.base import DetectorContext


@pytest.fixture(autouse=True)
def _enable_quantum_detectors(monkeypatch):
    monkeypatch.setenv("HG_QUANTUM_NOISE_CHARACTERIZATION_ENABLED", "true")
    monkeypatch.setenv("HG_QUANTUM_STATE_CORRELATION_ENABLED", "true")


def test_build_standard_detectors_includes_quantum_when_flags_on():
    detectors = build_standard_detectors()
    types = {type(d) for d in detectors}
    assert QuantumNoiseDetector in types
    assert EntanglementAnomalyDetector in types


def test_quantum_noise_detector_runs_on_steps():
    from hg_cognition.embeddings.hashing import hash_embed

    ctx = DetectorContext(
        correlation_id="corr-q",
        baseline_intent_vec=hash_embed("baseline"),
        baseline_response_vec=hash_embed("response"),
        baseline_diversity=0.35,
        baseline_alternatives=1.0,
        denied_intent_centroids=[],
    )
    steps = [
        StepTrace(
            ts=1.0,
            correlation_id="corr-q",
            run_id="r1",
            node_id="n1",
            actor_id="a1",
            role="assistant",
            input_text="hi",
            output_text="noisy output with variance",
            constraints=[],
            constraints_satisfied=[],
            verifications_expected=0,
            verifications_performed=0,
            planned_alternatives=1,
            tool_calls=[],
        )
    ]
    score = QuantumNoiseDetector().run(steps, ctx)
    assert score.level >= 0
