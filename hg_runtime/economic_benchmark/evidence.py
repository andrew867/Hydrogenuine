"""Evidence-quality records.

Evidence quality is an advisory signal about how strong the evidence behind a case is.
It never gates GREEN on its own and never authorizes anything; verification, hashing,
and safety do the gating.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.economic_benchmark.schemas import (
    EVIDENCE_QUALITY_RECORD_SCHEMA,
    EVIDENCE_QUALITY_TIERS,
    EconomicBenchmarkError,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_fields,
)


def record_evidence_quality(payload: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("case_ref", "tier"))
    reject_authority_payload(payload)
    tier = str(payload["tier"]).strip().lower()
    if tier not in EVIDENCE_QUALITY_TIERS:
        raise EconomicBenchmarkError(f"unknown_evidence_tier:{tier}")
    record = {
        "schema": EVIDENCE_QUALITY_RECORD_SCHEMA,
        "case_ref": payload["case_ref"],
        "tier": tier,
        "rationale": payload.get("rationale", ""),
        "advisory_only": True,
        "gates_green": False,
        **neutral_flags(),
    }
    record["record_hash"] = canonical_hash(record)
    return record


__all__ = ["record_evidence_quality"]
