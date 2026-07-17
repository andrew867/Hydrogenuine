"""Benchmark suite records.

A suite groups economic-task cases and must declare at least one negative control,
so a suite that "passes everything" is detectable. A suite is a measurement
container -- never an authority grant.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.economic_benchmark.schemas import (
    BENCHMARK_SUITE_SCHEMA,
    EconomicBenchmarkError,
    as_list,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    reject_forbidden_claim_text,
    require_fields,
)


def create_benchmark_suite(payload: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("suite_id", "title", "domain"))
    reject_authority_payload(payload)
    reject_forbidden_claim_boundary(payload)
    reject_forbidden_claim_text(payload.get("title"), payload.get("summary"))
    negative_controls = as_list(payload, "negative_control_refs")
    if not negative_controls:
        raise EconomicBenchmarkError("suite_requires_negative_control")
    suite = {
        "schema": BENCHMARK_SUITE_SCHEMA,
        "suite_id": payload["suite_id"],
        "title": payload["title"],
        "domain": payload["domain"],
        "summary": payload.get("summary", ""),
        "case_refs": list(as_list(payload, "case_refs")),
        "negative_control_refs": list(negative_controls),
        "claim_boundary": "benchmark_evidence_advisory_default",
        "advisory_only": True,
        **neutral_flags(),
    }
    suite["suite_hash"] = canonical_hash(suite)
    return suite


__all__ = ["create_benchmark_suite"]
