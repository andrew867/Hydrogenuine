from __future__ import annotations

import pytest

from hg_learning.guardrails.learnable_allowlist import AllowlistEntry, AllowlistViolation, load_allowlist
from hg_quantum.entanglement.shell_model import ShellModel
from hg_realtime.swarm.contracts import SwarmPlan


def _plan(tasks: list[dict]) -> SwarmPlan:
    return SwarmPlan(summary="test", tasks=tasks)


def test_assign_shells_deterministic():
    tasks = [
        {"entity_id": "p1", "role": "planner"},
        {"entity_id": "w1", "role": "worker", "traits": {"analysis_vs_intuition": 0.8}},
        {"entity_id": "w2", "role": "worker", "traits": {"analysis_vs_intuition": 0.8}},
        {"entity_id": "v1", "role": "verifier"},
    ]
    model = ShellModel()
    a = model.assign_shells(_plan(tasks))
    b = model.assign_shells(_plan(tasks))
    assert a.to_dict() == b.to_dict()


def test_assign_shells_covers_all_entities():
    tasks = [{"entity_id": f"e{i}", "role": "worker"} for i in range(5)]
    assignment = ShellModel().assign_shells(_plan(tasks))
    covered = set(assignment.entity_shell)
    assert covered == {f"e{i}" for i in range(5)}
    assert len(covered) == sum(len(v) for v in assignment.shells.values())


def test_coupling_same_shell_uses_trait_factor():
    model = ShellModel(kappa_intra=1.0, kappa_inter=0.15)
    tasks = [
        {"entity_id": "w1", "role": "worker", "traits": {"analysis_vs_intuition": 0.9}},
        {"entity_id": "w2", "role": "worker", "traits": {"analysis_vs_intuition": 0.7}},
    ]
    assignment = model.assign_shells(_plan(tasks))
    strength = model.coupling_strength("w1", "w2", assignment)
    assert strength == pytest.approx(0.8, abs=0.01)


def test_coupling_cross_shell_capped():
    model = ShellModel(kappa_intra=1.0, kappa_inter=0.15)
    tasks = [
        {"entity_id": "p1", "role": "planner", "traits": {"analysis_vs_intuition": 0.9}},
        {"entity_id": "w1", "role": "worker", "traits": {"analysis_vs_intuition": 0.9}},
    ]
    assignment = model.assign_shells(_plan(tasks))
    strength = model.coupling_strength("p1", "w1", assignment)
    assert strength == pytest.approx(0.15, abs=0.01)


def test_cross_shell_coupling_flat_in_population():
    model = ShellModel(kappa_intra=1.0, kappa_inter=0.15)
    small = _plan(
        [{"entity_id": "p1", "role": "planner"}]
        + [{"entity_id": f"w{i}", "role": "worker"} for i in range(2)]
    )
    large = _plan(
        [{"entity_id": "p1", "role": "planner"}]
        + [{"entity_id": f"w{i}", "role": "worker"} for i in range(10)]
    )
    a_small = model.assign_shells(small)
    a_large = model.assign_shells(large)
    s1 = model.coupling_strength("p1", "w0", a_small)
    s2 = model.coupling_strength("p1", "w0", a_large)
    assert s1 == s2


def test_shell_filling_recommends_current_shell_first():
    tasks = [{"entity_id": "v1", "role": "verifier"}]
    assignment = ShellModel().assign_shells(_plan(tasks))
    advice = ShellModel().shell_filling_recommendation(
        assignment,
        {"limiting_shell": "verifier", "shell_quality": {"verifier": 0.3}},
    )
    assert advice.action == "fill_current_shell"
    assert advice.target_shell == "verifier"


def test_kappa_parameters_are_allowlisted_learnables():
    allowlist = load_allowlist()
    intra = allowlist.get("shell_model.kappa_intra")
    inter = allowlist.get("shell_model.kappa_inter")
    assert intra is not None
    assert inter is not None
    assert intra.floor <= intra.default <= intra.ceiling
    assert inter.floor <= inter.default <= inter.ceiling
    with pytest.raises(AllowlistViolation):
        allowlist.register_parameter(
            AllowlistEntry(
                key="shell_model.kappa_intra",
                path="shell_model",
                floor=0.0,
                ceiling=10.0,
                default=5.0,
            )
        )
    with pytest.raises(AllowlistViolation):
        allowlist.validate_write("shell_model.kappa_unlisted", 1.0, path_name="shell_model")
