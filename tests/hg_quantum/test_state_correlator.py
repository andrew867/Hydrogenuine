from __future__ import annotations

import time

import pytest

from hg_quantum.entanglement.state_correlator import StateCorrelator


def test_register_pair_creates_entangled_pair():
    corr = StateCorrelator(fingerprint_id="fp1")
    pair = corr.register_pair("a", "b", "fingerprint_shared")
    assert pair.entity_a in ("a", "b")
    assert pair.initial_correlation == 1.0


def test_register_pair_invalid_type_raises():
    corr = StateCorrelator()
    with pytest.raises(ValueError, match="invalid correlation_type"):
        corr.register_pair("a", "b", "bogus")


def test_propagate_state_change_updates_partner():
    corr = StateCorrelator()
    corr.register_pair("a", "b", "task_coupled", initial_correlation=0.9)
    results = corr.propagate_state_change("a", {"emotional": 0.3})
    assert len(results) == 1
    assert results[0].target_entity == "b"
    assert results[0].applied_delta["emotional"] == pytest.approx(0.27, abs=0.05)


def test_propagate_state_change_no_partner_is_noop():
    corr = StateCorrelator()
    assert corr.propagate_state_change("c", {"emotional": 0.3}) == []


def test_correlation_decays_over_time():
    corr = StateCorrelator(decay_half_life_s=1.0)
    corr.register_pair("a", "b", "task_coupled", initial_correlation=1.0)
    key = corr._pair_key("a", "b")
    corr._last_interaction[key] = time.time() - 3600
    strength = corr.measure_correlation("a", "b")
    assert strength.coefficient < 1.0


def test_measure_correlation_returns_decomposition():
    corr = StateCorrelator()
    corr.register_pair("a", "b", "task_coupled")
    corr._dimension_state["a"] = {"emotional": 0.8}
    corr._dimension_state["b"] = {"emotional": 0.2}
    strength = corr.measure_correlation("a", "b")
    assert "emotional" in strength.by_dimension or strength.by_dimension


def test_state_correlator_shell_sibling_uses_shell_coupling():
    from hg_quantum.entanglement.contracts import ShellAssignment
    from hg_quantum.entanglement.shell_model import ShellModel

    assignment = ShellAssignment(
        shells={"planner": ["p1"], "worker": ["w1", "w2"], "verifier": [], "integrator": []},
        entity_shell={"p1": "planner", "w1": "worker", "w2": "worker"},
    )
    model = ShellModel(kappa_intra=1.0, kappa_inter=0.15)
    corr = StateCorrelator(shell_assignment=assignment, shell_model=model)
    intra = corr.register_pair("w1", "w2", "shell_sibling")
    inter = corr.register_pair("p1", "w1", "shell_sibling")
    assert intra.initial_correlation > inter.initial_correlation
    results = corr.propagate_state_change("p1", {"emotional": 1.0})
    partner = [r for r in results if r.target_entity == "w1"]
    assert partner
    assert partner[0].applied_delta["emotional"] < 0.5
