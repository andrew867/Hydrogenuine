"""Field-trial candidate records (advisory only).

A field-trial candidate is a *suggestion* that a passed, verified, held-out case
might be worth a Phase 35 field trial. It is advisory only, carries no authority,
and must be re-gated by Phase 35 before any live work. This module never implements
Phase 35; it only refuses to emit an authorized or unbounded candidate.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.economic_benchmark.schemas import (
    FIELD_TRIAL_CANDIDATE_SCHEMA,
    EconomicBenchmarkError,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    require_fields,
)


def propose_field_trial_candidate(
    payload: Mapping[str, Any],
    *,
    outcome: Mapping[str, Any],
    control=None,
) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("candidate_id", "suite_ref", "case_ref"))
    reject_authority_payload(payload)
    reject_forbidden_claim_boundary(payload)

    # Only a passed, verified, held-out case may become a candidate, and only advisory.
    if outcome.get("status") != "pass" or not outcome.get("green"):
        raise EconomicBenchmarkError("field_trial_candidate_requires_passed_verified_scope")
    if not outcome.get("held_out"):
        raise EconomicBenchmarkError("heldout_scope_required_for_field_trial_candidate")

    candidate = {
        "schema": FIELD_TRIAL_CANDIDATE_SCHEMA,
        "candidate_id": payload["candidate_id"],
        "suite_ref": payload["suite_ref"],
        "case_ref": payload["case_ref"],
        "rationale": payload.get("rationale", ""),
        "advisory_only": True,
        "requires_phase35_regating": True,
        "is_live_permit": False,
        "is_deployment_approval": False,
        "claim_boundary": "benchmark_evidence_advisory_default",
        **neutral_flags(),
    }
    candidate["candidate_hash"] = canonical_hash(candidate)
    return candidate


def assert_candidate_is_advisory(candidate: Mapping[str, Any]) -> Mapping[str, Any]:
    """Refuse any field-trial candidate that claims to be a permit or Phase 35 pass."""
    reject_authority_payload(dict(candidate))
    if candidate.get("is_live_permit") or candidate.get("is_deployment_approval"):
        raise EconomicBenchmarkError("field_trial_candidate_is_advisory_only")
    if not candidate.get("requires_phase35_regating", True):
        raise EconomicBenchmarkError("field_trial_candidate_requires_phase35_regating")
    return candidate


__all__ = ["assert_candidate_is_advisory", "propose_field_trial_candidate"]
