from __future__ import annotations

from hg_quantum.coordination.kpz_predictor import KpzTransportPredictor


def test_kpz_predicts_swarm_size():
    pred = KpzTransportPredictor()
    result = pred.predict("writing", correlation_density=0.6)
    assert 2 <= result.recommended_size <= 10
    assert result.warmup_seconds > 0
    assert 0 < result.noise_threshold < 1


def test_kpz_benchmark_observed():
    pred = KpzTransportPredictor()
    p = pred.predict("coding")
    bench = pred.compare_observed(p, {"swarm_size": 6, "warmup_seconds": 16.0, "noise_magnitude": 0.4})
    assert bench["deltas"]["size"] is not None
    summary = pred.benchmark_summary()
    assert summary["count"] == 1
