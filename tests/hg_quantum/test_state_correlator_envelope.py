from __future__ import annotations

import time

from hg_quantum.entanglement.state_correlator import StateCorrelator


def test_envelope_absent_matches_exponential_decay():
    correlator = StateCorrelator(decay_half_life_s=100.0)
    key = ("a", "b")
    correlator._live_correlation[key] = 1.0
    correlator._last_interaction[key] = time.time() - 100.0
    baseline = correlator._decayed_correlation(key, time.time())
    assert 0.45 < baseline < 0.55


def test_task_envelope_multiplier_slows_decay():
    correlator = StateCorrelator(
        decay_half_life_s=100.0,
        task_envelope={"research": 2.0},
    )
    key = ("a", "b")
    correlator._live_correlation[key] = 1.0
    correlator._last_interaction[key] = time.time() - 100.0
    with_envelope = correlator._decayed_correlation(key, time.time(), task_class="research")
    without = correlator._decayed_correlation(key, time.time())
    assert with_envelope > without
