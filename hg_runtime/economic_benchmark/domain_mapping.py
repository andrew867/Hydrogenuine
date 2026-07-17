"""Benchmark-case to domain-pack mapping records.

A domain pack tells the suite which domain a case belongs to. The mapping is
advisory only: a domain pack is never permission to act in that domain.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.economic_benchmark.schemas import (
    BENCHMARK_TASK_DOMAIN_MAPPING_SCHEMA,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)


def map_case_to_domain_pack(payload: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("case_ref", "domain_pack_ref"))
    reject_authority_payload(payload)
    reject_forbidden_claim_boundary(payload)
    mapping = {
        "schema": BENCHMARK_TASK_DOMAIN_MAPPING_SCHEMA,
        "case_ref": payload["case_ref"],
        "domain_pack_ref": payload["domain_pack_ref"],
        "rationale": payload.get("rationale", ""),
        "advisory_only": True,
        "domain_pack_is_permission": False,
        "claim_boundary": "benchmark_evidence_advisory_default",
        **neutral_flags(),
    }
    mapping["mapping_hash"] = canonical_hash(mapping)
    return mapping


__all__ = ["map_case_to_domain_pack"]
