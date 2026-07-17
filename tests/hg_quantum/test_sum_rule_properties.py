from __future__ import annotations

import pytest

from hg_quantum.error_correction.sum_rule_engine import SYNDROME_CLASSES, SumRuleEngine


@pytest.mark.parametrize("amount", [0.01, 0.02, 0.05])
def test_conservation_under_transfer_sequence(amount: float):
    engine = SumRuleEngine(safety_floor=0.1)
    inv = engine.estimate_capacity(entity_count=10, token_budget=25000, latency_ceiling_ms=800)
    engine.allocate({c: 1.0 for c in SYNDROME_CLASSES})
    total_before = sum(engine.current_allocation().by_class.values())
    engine.transfer("style", "logical", amount)
    engine.transfer("format", "factual", amount)
    total_after = sum(engine.current_allocation().by_class.values())
    assert total_before == pytest.approx(total_after, abs=1e-5)


def test_nonnegativity_after_transfers():
    engine = SumRuleEngine()
    inv = engine.estimate_capacity(entity_count=5, token_budget=12000, latency_ceiling_ms=500)
    engine.allocate({c: 1.0 for c in SYNDROME_CLASSES})
    engine.transfer("crosstalk", "logical", 0.02)
    for v in engine.current_allocation().by_class.values():
        assert v >= -1e-9


def test_safety_floor_unreachable():
    engine = SumRuleEngine(safety_floor=0.1)
    inv = engine.estimate_capacity(entity_count=5, token_budget=12000, latency_ceiling_ms=500)
    alloc = engine.allocate({c: 0.0 for c in SYNDROME_CLASSES})
    assert alloc.by_class["safety"] >= engine.safety_floor
