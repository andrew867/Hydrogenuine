from __future__ import annotations

from hg_quantum.entanglement.dissipative_stabilizer import DissipativeStabilizer


def test_stabilizer_reduces_energy():
    stabilizer = DissipativeStabilizer(damping=0.3)
    states = [
        {"x": 0.1, "y": 0.9},
        {"x": 0.9, "y": 0.1},
        {"x": 0.2, "y": 0.8},
        {"x": 0.8, "y": 0.2},
    ]
    before = stabilizer.system_energy(states)
    after_states = stabilizer.stabilize(states, iterations=50)
    after = stabilizer.system_energy(after_states)
    assert after <= before
