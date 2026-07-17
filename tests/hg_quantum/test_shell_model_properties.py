from __future__ import annotations

import itertools

import pytest

from hg_quantum.entanglement.shell_model import ShellModel
from hg_realtime.swarm.contracts import SwarmPlan


@pytest.mark.parametrize(
    "kappa_intra,kappa_inter",
    [(1.0, 0.15), (0.8, 0.1), (0.6, 0.2)],
)
def test_coupling_symmetry(kappa_intra: float, kappa_inter: float):
    model = ShellModel(kappa_intra=kappa_intra, kappa_inter=kappa_inter)
    tasks = [
        {"entity_id": "p1", "role": "planner"},
        {"entity_id": "w1", "role": "worker"},
        {"entity_id": "w2", "role": "worker"},
    ]
    assignment = model.assign_shells(SwarmPlan(summary="t", tasks=tasks))
    for a, b in itertools.combinations(assignment.entity_shell, 2):
        assert model.coupling_strength(a, b, assignment) == pytest.approx(
            model.coupling_strength(b, a, assignment)
        )


@pytest.mark.parametrize("kappa_intra", [0.5, 0.75, 1.0])
def test_coupling_bounds(kappa_intra: float):
    model = ShellModel(kappa_intra=kappa_intra, kappa_inter=0.15)
    tasks = [{"entity_id": f"e{i}", "role": "worker"} for i in range(4)]
    assignment = model.assign_shells(SwarmPlan(summary="t", tasks=tasks))
    for a, b in itertools.combinations(assignment.entity_shell, 2):
        s = model.coupling_strength(a, b, assignment)
        assert 0.0 <= s <= kappa_intra


def test_intra_dominates_inter():
    model = ShellModel(kappa_intra=1.0, kappa_inter=0.15)
    tasks = [
        {"entity_id": "p1", "role": "planner", "traits": {"x": 0.5}},
        {"entity_id": "w1", "role": "worker", "traits": {"x": 0.5}},
        {"entity_id": "w2", "role": "worker", "traits": {"x": 0.5}},
    ]
    assignment = model.assign_shells(SwarmPlan(summary="t", tasks=tasks))
    intra = model.coupling_strength("w1", "w2", assignment, trait_factor_override=0.8)
    inter = model.coupling_strength("p1", "w1", assignment, trait_factor_override=0.8)
    assert intra >= inter
