"""Benchmark cost records and model-route cost records.

A cost record captures what a case cost to run. When a model did work, the cost
record must reference a Phase 33 model-route receipt. Both the cost record and the
referenced model route are advisory only -- a route or its cost never grants
authority or permission.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.economic_benchmark.schemas import (
    BENCHMARK_COST_RECORD_SCHEMA,
    MODEL_COST_RECORD_SCHEMA,
    EconomicBenchmarkError,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_fields,
)


def record_model_cost(payload: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    """Record the cost of a model route, referencing a Phase 33 route receipt (fixture/dry-run)."""
    preempt_if_needed(control)
    require_fields(payload, ("case_ref", "model_route_receipt_ref"))
    reject_authority_payload(payload)
    record = {
        "schema": MODEL_COST_RECORD_SCHEMA,
        "case_ref": payload["case_ref"],
        "model_route_receipt_ref": payload["model_route_receipt_ref"],
        "tokens_in": int(payload.get("tokens_in", 0)),
        "tokens_out": int(payload.get("tokens_out", 0)),
        "wall_clock_seconds": float(payload.get("wall_clock_seconds", 0.0)),
        "advisory_only": True,
        "model_route_is_permission": False,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record


def record_cost(payload: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    """Record the overall cost of a case. Must reference a model-route receipt when a model ran."""
    preempt_if_needed(control)
    require_fields(payload, ("case_ref",))
    reject_authority_payload(payload)
    used_model = bool(payload.get("used_model", True))
    route_ref = payload.get("model_route_receipt_ref")
    if used_model and not route_ref:
        raise EconomicBenchmarkError("cost_record_requires_model_route_receipt")
    record = {
        "schema": BENCHMARK_COST_RECORD_SCHEMA,
        "case_ref": payload["case_ref"],
        "used_model": used_model,
        "model_route_receipt_ref": route_ref or "",
        "model_cost_refs": list(payload.get("model_cost_refs", [])),
        "compute_seconds": float(payload.get("compute_seconds", 0.0)),
        "human_minutes": float(payload.get("human_minutes", 0.0)),
        "advisory_only": True,
        "model_route_is_permission": False,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record


__all__ = ["record_cost", "record_model_cost"]
