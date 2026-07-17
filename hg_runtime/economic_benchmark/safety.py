"""Benchmark safety records.

A safety record captures whether a case cleared safety review. A safety failure is
recorded honestly and blocks GREEN even when the task score is high; it is never
averaged away.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.economic_benchmark.schemas import (
    BENCHMARK_SAFETY_RECORD_SCHEMA,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_fields,
)


def record_safety_result(payload: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("case_ref", "passed"))
    reject_authority_payload(payload)
    passed = bool(payload["passed"])
    record = {
        "schema": BENCHMARK_SAFETY_RECORD_SCHEMA,
        "case_ref": payload["case_ref"],
        "passed": passed,
        "violations": list(payload.get("violations", [])),
        "reviewer": payload.get("reviewer", ""),
        "blocks_green": not passed,
        "advisory_only": True,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record


__all__ = ["record_safety_result"]
