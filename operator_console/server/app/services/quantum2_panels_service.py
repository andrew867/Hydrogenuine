"""Quantum-2 structure track operator panels (Q2.1–Q2.3)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from hg_quantum.error_correction.sum_rule_engine import SumRuleEngine
from hg_quantum.telemetry import QUANTUM_METRIC_NAMES

_ENGINE = SumRuleEngine()


def get_sum_rule_state() -> Dict[str, Any]:
    inv = _ENGINE.current_invariant()
    alloc = _ENGINE.current_allocation()
    ledger = [r.to_dict() for r in _ENGINE.transfer_ledger()]
    return {
        "ok": True,
        "invariant": inv.to_dict() if inv else None,
        "allocation": alloc.to_dict() if alloc else None,
        "transfer_ledger": ledger,
        "metrics_available": [m for m in QUANTUM_METRIC_NAMES if m.startswith("hg_quantum_sumrule")],
    }


def estimate_sum_rule_capacity(
    *,
    entity_count: int,
    token_budget: float,
    latency_ceiling_ms: float,
) -> Dict[str, Any]:
    inv = _ENGINE.estimate_capacity(
        entity_count=entity_count,
        token_budget=token_budget,
        latency_ceiling_ms=latency_ceiling_ms,
    )
    return {"ok": True, "invariant": inv.to_dict()}


def allocate_sum_rule(task_risk_profile: Dict[str, float]) -> Dict[str, Any]:
    try:
        alloc = _ENGINE.allocate(task_risk_profile)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "allocation": alloc.to_dict()}


def transfer_sum_rule(
    *,
    from_class: str,
    to_class: str,
    amount: float,
    actor_id: str = "operator",
    rationale: str = "",
) -> Dict[str, Any]:
    try:
        record = _ENGINE.transfer(
            from_class,
            to_class,
            amount,
            actor_id=actor_id,
            rationale=rationale,
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "transfer": record.to_dict(), "allocation": _ENGINE.current_allocation().to_dict()}


def audit_sum_rule(telemetry: Dict[str, Any]) -> Dict[str, Any]:
    report = _ENGINE.audit(telemetry)
    metrics = {
        "hg_quantum_sumrule_capacity": report.expected_total,
        "hg_quantum_sumrule_observed_total": report.observed_total,
        "hg_quantum_sumrule_violation": 1.0 if report.violation else 0.0,
        "hg_quantum_sumrule_unaccounted_leak": report.unaccounted_leak,
    }
    alloc = _ENGINE.current_allocation()
    if alloc:
        metrics["hg_quantum_sumrule_allocated_total"] = sum(alloc.by_class.values())
    return {"ok": True, "report": report.to_dict(), "metrics": metrics}
