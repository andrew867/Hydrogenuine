from __future__ import annotations

from hg_quantum.entanglement.symmetry_breaker import SymmetryBreaker


BASE_FP = {"cognitive_fingerprint": {"analysis_vs_intuition": 0.5}}


def test_compute_offsets_paired_opposites():
    breaker = SymmetryBreaker()
    offsets = breaker.compute_offsets(BASE_FP, 4, {"task_type": "analytical"})
    axis = "analysis_vs_intuition"
    assert offsets[0][axis] > 0
    assert offsets[3][axis] < 0
    assert offsets[1][axis] > 0
    assert offsets[2][axis] < 0


def test_compute_offsets_odd_swarm_has_neutral_center():
    breaker = SymmetryBreaker()
    offsets = breaker.compute_offsets(BASE_FP, 5, {"task_type": "analytical"})
    assert offsets[2]["analysis_vs_intuition"] == 0.0


def test_compute_offsets_creative_task_uses_exploration_axis():
    breaker = SymmetryBreaker()
    offsets = breaker.compute_offsets(BASE_FP, 4, {"task_type": "creative"})
    assert "structure_vs_exploration" in offsets[0]


def test_compute_offsets_adversarial_task_uses_agreement_axis():
    breaker = SymmetryBreaker()
    offsets = breaker.compute_offsets(BASE_FP, 4, {"task_type": "adversarial_review"})
    assert "agreement_tendency" in offsets[0]


def test_symmetry_breaker_pairs_within_shell_only():
    from hg_quantum.entanglement.contracts import ShellAssignment
    from hg_quantum.entanglement.symmetry_breaker import SymmetryBreaker

    assignment = ShellAssignment(
        shells={
            "planner": ["p1", "p2"],
            "worker": ["w1", "w2", "w3", "w4"],
            "verifier": [],
            "integrator": [],
        },
        entity_shell={
            "p1": "planner",
            "p2": "planner",
            "w1": "worker",
            "w2": "worker",
            "w3": "worker",
            "w4": "worker",
        },
    )
    order = ["p1", "p2", "w1", "w2", "w3", "w4"]
    breaker = SymmetryBreaker()
    offsets = breaker.compute_offsets_with_shells(
        BASE_FP,
        assignment,
        {"task_type": "analytical"},
        entity_order=order,
    )
    axis = "analysis_vs_intuition"
    assert offsets[0][axis] * offsets[1][axis] < 0
    assert offsets[2][axis] * offsets[5][axis] < 0
