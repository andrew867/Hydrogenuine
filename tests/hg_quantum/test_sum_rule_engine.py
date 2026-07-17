from __future__ import annotations

import pytest

from hg_quantum.error_correction.sum_rule_engine import SYNDROME_CLASSES, SumRuleEngine


def test_estimate_and_allocate_conserves_total():
    engine = SumRuleEngine()
    inv = engine.estimate_capacity(entity_count=8, token_budget=20000, latency_ceiling_ms=500)
    alloc = engine.allocate(
        {"factual": 0.4, "logical": 0.3, "style": 0.1, "format": 0.1, "crosstalk": 0.1, "safety": 0.2}
    )
    assert sum(alloc.by_class.values()) == pytest.approx(inv.total_capacity, abs=1e-5)


def test_transfer_zero_sum():
    engine = SumRuleEngine()
    inv = engine.estimate_capacity(entity_count=4, token_budget=10000, latency_ceiling_ms=400)
    engine.allocate({c: 1.0 for c in SYNDROME_CLASSES})
    before = dict(engine.current_allocation().by_class)
    engine.transfer("style", "factual", 0.05, actor_id="op1")
    after = engine.current_allocation().by_class
    assert sum(before.values()) == pytest.approx(sum(after.values()), abs=1e-5)
    assert len(engine.transfer_ledger()) == 1


def test_safety_floor_transfer_rejected():
    engine = SumRuleEngine(safety_floor=0.1)
    inv = engine.estimate_capacity(entity_count=4, token_budget=10000, latency_ceiling_ms=400)
    engine.allocate({c: 1.0 for c in SYNDROME_CLASSES})
    with pytest.raises(ValueError, match="safety"):
        engine.transfer("safety", "factual", 0.01)
    with pytest.raises(ValueError, match="safety"):
        engine.transfer("factual", "safety", 0.01)


def test_audit_flags_violation():
    engine = SumRuleEngine()
    inv = engine.estimate_capacity(entity_count=4, token_budget=10000, latency_ceiling_ms=400)
    report = engine.audit({"observed_total": inv.total_capacity + 0.5, "expected_total": inv.total_capacity})
    assert report.violation is True
    assert report.unaccounted_leak > 0


def test_uniform_allocation_baseline():
    engine = SumRuleEngine()
    inv = engine.estimate_capacity(entity_count=6, token_budget=15000, latency_ceiling_ms=600)
    uniform = engine.uniform_allocation(inv)
    assert sum(uniform.by_class.values()) == pytest.approx(inv.total_capacity, abs=1e-5)
