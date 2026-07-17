"""Benchmark claim-scope records.

A claim scope says exactly what the benchmark evidence supports. It is bounded to
passed, verified, held-out cases only. It can never claim AGI, human-level economic
capability, the ability to perform any economic task, or broad competence; and it can
never widen authority or claim scope beyond the tested, verified cases.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.economic_benchmark.schemas import (
    BENCHMARK_CLAIM_SCOPE_SCHEMA,
    EconomicBenchmarkError,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    reject_forbidden_claim_text,
    require_fields,
)


def _passed_verified_heldout(outcomes: Iterable[Mapping[str, Any]]) -> list[str]:
    bounded: list[str] = []
    for outcome in outcomes:
        if outcome.get("is_negative_control"):
            continue
        if outcome.get("status") == "pass" and outcome.get("held_out") and outcome.get("green"):
            bounded.append(str(outcome.get("case_id")))
    return bounded


def build_claim_scope(
    payload: Mapping[str, Any],
    *,
    outcomes: Iterable[Mapping[str, Any]] = (),
    control=None,
) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("suite_ref", "statement"))
    reject_authority_payload(payload)
    reject_forbidden_claim_boundary(payload)
    reject_forbidden_claim_text(payload.get("statement"), payload.get("summary"))

    bounded_cases = _passed_verified_heldout(outcomes)
    declared = list(payload.get("supporting_case_refs", []))
    # A claim may not reach beyond passed/verified/held-out cases when outcomes are supplied.
    if declared and outcomes:
        overreach = [ref for ref in declared if ref not in bounded_cases]
        if overreach:
            raise EconomicBenchmarkError(f"claim_scope_overreaches_unverified_cases:{','.join(overreach)}")
    supporting = declared or bounded_cases

    scope = {
        "schema": BENCHMARK_CLAIM_SCOPE_SCHEMA,
        "suite_ref": payload["suite_ref"],
        "statement": payload["statement"],
        "supporting_case_refs": supporting,
        "bounded_to_passed_verified_heldout": True,
        "claims_agi": False,
        "claims_any_economic_task": False,
        "claims_human_level_economic": False,
        "claims_broad_competence": False,
        "claim_boundary": "benchmark_evidence_advisory_default",
        "advisory_only": True,
        **neutral_flags(),
    }
    scope["scope_hash"] = canonical_hash(scope)
    return scope


def assert_claim_not_widened(scope: Mapping[str, Any], *, allowed_case_refs: Iterable[str]) -> Mapping[str, Any]:
    """Defensive guard: a claim scope may not reference cases outside the allowed verified set."""
    reject_authority_payload(dict(scope))
    allowed = set(str(ref) for ref in allowed_case_refs)
    overreach = [ref for ref in scope.get("supporting_case_refs", []) if str(ref) not in allowed]
    if overreach:
        raise EconomicBenchmarkError(f"benchmark_result_cannot_widen_claim_scope:{','.join(overreach)}")
    return scope


__all__ = ["assert_claim_not_widened", "build_claim_scope"]
