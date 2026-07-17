from __future__ import annotations

from hg_quantum.noise_model.noise_budget import allocate_noise_budget, match_demand_supply


def test_demand_supply_mismatch_surfaces_operator_decision():
    budget = allocate_noise_budget("e1", total_budget=2.0, stages=["plan", "execute"])
    result = match_demand_supply(budget, scrutiny_capacity=1.0)
    assert result["operator_decision_required"] is True
    assert result["gap"] > 0
