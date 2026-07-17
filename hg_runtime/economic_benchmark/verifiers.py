"""Benchmark verifier definitions and verification-result records.

Every case needs a verifier. A verification result records pass/fail plus evidence
refs. A verification failure is recorded honestly and blocks GREEN; it is never
averaged away or hidden.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.economic_benchmark.schemas import (
    BENCHMARK_VERIFIER_SCHEMA,
    VERIFICATION_RESULT_SCHEMA,
    VERIFIER_KINDS,
    EconomicBenchmarkError,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    require_fields,
)


def define_verifier(payload: Mapping[str, Any], *, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("verifier_id", "kind"))
    reject_authority_payload(payload)
    kind = str(payload["kind"]).strip().lower()
    if kind not in VERIFIER_KINDS:
        raise EconomicBenchmarkError(f"unknown_verifier_kind:{kind}")
    verifier = {
        "schema": BENCHMARK_VERIFIER_SCHEMA,
        "verifier_id": payload["verifier_id"],
        "kind": kind,
        "description": payload.get("description", ""),
        "deterministic": bool(payload.get("deterministic", True)),
        "advisory_only": True,
        **neutral_flags(),
    }
    verifier["verifier_hash"] = canonical_hash(verifier)
    return verifier


def run_verification(
    verifier: Mapping[str, Any],
    *,
    case_ref: str,
    passed: bool,
    evidence_refs: list[str] | None = None,
    detail: str = "",
    control=None,
) -> dict[str, Any]:
    preempt_if_needed(control)
    if not verifier or not verifier.get("verifier_id"):
        raise EconomicBenchmarkError("missing_verifier")
    evidence = list(evidence_refs or [])
    if passed and not evidence:
        raise EconomicBenchmarkError("passing_verification_requires_evidence")
    result = {
        "schema": VERIFICATION_RESULT_SCHEMA,
        "verifier_ref": verifier["verifier_id"],
        "case_ref": case_ref,
        "passed": bool(passed),
        "evidence_refs": evidence,
        "detail": detail,
        "advisory_only": True,
        **neutral_flags(),
    }
    result["result_hash"] = canonical_hash(result)
    return result


__all__ = ["define_verifier", "run_verification"]
