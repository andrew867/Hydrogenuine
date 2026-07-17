"""Benchmark run receipts and suite results.

A suite result preserves every case outcome, including failures and qualified
(human-disagreement) cases -- nothing is hidden or averaged away. A suite is GREEN
only when every scored case passed, every negative control failed as expected, and
receipts back the run. A green claim over any failing case is fake green. A result
record is evidence, never permission.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.economic_benchmark.schemas import (
    BENCHMARK_RESULT_SCHEMA,
    BENCHMARK_RUN_RECEIPT_SCHEMA,
    GREEN_LIKE,
    EconomicBenchmarkError,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
)


def build_benchmark_run_receipt(
    *,
    suite_ref: str,
    status: str,
    receipt_refs: list[str],
    summary: Mapping[str, Any] | None = None,
    control=None,
) -> dict[str, Any]:
    preempt_if_needed(control)
    if str(status).lower() in GREEN_LIKE and not receipt_refs:
        raise EconomicBenchmarkError("missing_receipt_blocks_success")
    receipt = {
        "schema": BENCHMARK_RUN_RECEIPT_SCHEMA,
        "suite_ref": suite_ref,
        "status": status,
        "receipt_refs": list(receipt_refs),
        "summary": dict(summary or {}),
        "is_permission": False,
        "advisory_only": True,
        **neutral_flags(),
    }
    receipt["receipt_hash"] = canonical_hash(receipt)
    return receipt


def generate_suite_result(
    suite: Mapping[str, Any],
    outcomes: Iterable[Mapping[str, Any]],
    *,
    negative_control_outcomes: Iterable[Mapping[str, Any]] = (),
    receipt_refs: list[str] | None = None,
    claim_scope_ref: str | None = None,
    leakage_detected: bool = False,
    control=None,
) -> dict[str, Any]:
    preempt_if_needed(control)
    cases = list(outcomes)
    controls = list(negative_control_outcomes)
    reasons: list[str] = []

    failed = [o for o in cases if o.get("status") == "fail"]
    qualified = [o for o in cases if o.get("status") == "qualified"]
    passed = [o for o in cases if o.get("status") == "pass" and o.get("green")]

    if failed:
        reasons.append("failing_cases_present")
    if qualified:
        reasons.append("qualified_cases_present")
    if leakage_detected:
        reasons.append("leakage_detected")

    # Negative controls are required and must fail as expected.
    if not controls:
        reasons.append("negative_control_required")
    unexpected = [o for o in controls if o.get("status") == "pass" and o.get("green")]
    if unexpected:
        reasons.append("negative_control_passes_unexpectedly")

    if not (receipt_refs or []):
        reasons.append("missing_receipt")

    green = not reasons
    status = "green" if green else "red"

    result = {
        "schema": BENCHMARK_RESULT_SCHEMA,
        "suite_ref": suite.get("suite_id"),
        "status": status,
        "green": green,
        "reasons": reasons,
        # Failures and qualified cases are preserved, never hidden.
        "cases": cases,
        "negative_control_outcomes": controls,
        "passed_case_ids": [o.get("case_id") for o in passed],
        "failed_case_ids": [o.get("case_id") for o in failed],
        "qualified_case_ids": [o.get("case_id") for o in qualified],
        "passed_verified_heldout_case_ids": [
            o.get("case_id") for o in passed if o.get("held_out")
        ],
        "receipt_refs": list(receipt_refs or []),
        "claim_scope_ref": claim_scope_ref or "",
        "claim_boundary": "benchmark_evidence_advisory_default",
        "advisory_only": True,
        **neutral_flags(),
    }
    result["result_hash"] = canonical_hash(result)
    return result


def assert_not_fake_green(result: Mapping[str, Any]) -> Mapping[str, Any]:
    """Refuse a GREEN result that hides failing/qualified cases or unexpectedly-passing controls."""
    reject_authority_payload(dict(result))
    if not result.get("green"):
        return result
    if any(o.get("status") != "pass" or not o.get("green") for o in result.get("cases", [])):
        raise EconomicBenchmarkError("fake_green_rejected:failing_case_counted_as_pass")
    for ctrl in result.get("negative_control_outcomes", []):
        if ctrl.get("status") == "pass" and ctrl.get("green"):
            raise EconomicBenchmarkError("fake_green_rejected:negative_control_passed")
    return result


def assert_not_permission(record: Mapping[str, Any]) -> Mapping[str, Any]:
    """A benchmark record may never carry authority, permission, or a live permit."""
    reject_authority_payload(dict(record))
    return record


__all__ = [
    "assert_not_fake_green",
    "assert_not_permission",
    "build_benchmark_run_receipt",
    "generate_suite_result",
]
