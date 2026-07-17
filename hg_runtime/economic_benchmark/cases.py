"""Economic-task benchmark cases and per-case outcome evaluation.

A case may only be defined with a verifier, a domain-pack mapping, a workbench
artifact reference, an evidence-quality record, a cost record, a safety record, and
a claim scope. A case outcome is GREEN-eligible only when its artifact hash is
verified, its verifier passes, its safety record passes, no leakage is detected, and
any required human review carries no unresolved disagreement. Failed and qualified
cases are preserved, never hidden.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.economic_benchmark.schemas import (
    ECONOMIC_TASK_CASE_SCHEMA,
    EconomicBenchmarkError,
    neutral_flags,
    preempt_if_needed,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    reject_forbidden_claim_text,
    reject_network_and_credentials,
    require_fields,
)

# Required reference -> specific refusal message.
_REQUIRED_CASE_REFS = (
    ("verifier_ref", "task_case_requires_verifier"),
    ("domain_pack_mapping_ref", "benchmark_case_requires_domain_pack_mapping"),
    ("workbench_artifact_ref", "benchmark_case_requires_workbench_artifact_ref"),
    ("evidence_quality_ref", "benchmark_case_requires_evidence_quality_record"),
    ("cost_record_ref", "benchmark_case_requires_cost_record"),
    ("safety_record_ref", "benchmark_case_requires_safety_record"),
    ("claim_scope_ref", "benchmark_case_requires_claim_scope"),
)


def create_task_case(payload: Mapping[str, Any], *, allow_network: bool = False, control=None) -> dict[str, Any]:
    preempt_if_needed(control)
    require_fields(payload, ("case_id", "suite_ref", "task_statement"))
    reject_authority_payload(payload)
    reject_forbidden_claim_boundary(payload)
    reject_forbidden_claim_text(payload.get("task_statement"), payload.get("summary"))
    reject_network_and_credentials(
        payload.get("input_locator"),
        payload.get("resource_locator"),
        allow_network=allow_network,
    )
    for field, message in _REQUIRED_CASE_REFS:
        if not payload.get(field):
            raise EconomicBenchmarkError(message)
    case = {
        "schema": ECONOMIC_TASK_CASE_SCHEMA,
        "case_id": payload["case_id"],
        "suite_ref": payload["suite_ref"],
        "task_statement": payload["task_statement"],
        "verifier_ref": payload["verifier_ref"],
        "domain_pack_mapping_ref": payload["domain_pack_mapping_ref"],
        "workbench_artifact_ref": payload["workbench_artifact_ref"],
        "evidence_quality_ref": payload["evidence_quality_ref"],
        "cost_record_ref": payload["cost_record_ref"],
        "safety_record_ref": payload["safety_record_ref"],
        "claim_scope_ref": payload["claim_scope_ref"],
        "held_out": bool(payload.get("held_out", False)),
        "is_negative_control": bool(payload.get("is_negative_control", False)),
        "requires_human_review": bool(payload.get("requires_human_review", False)),
        "claim_boundary": "benchmark_evidence_advisory_default",
        "advisory_only": True,
        **neutral_flags(),
    }
    case["case_hash"] = canonical_hash(case)
    return case


def evaluate_case(
    case: Mapping[str, Any],
    *,
    verification_result: Mapping[str, Any] | None,
    safety_record: Mapping[str, Any] | None,
    artifact_hash_record: Mapping[str, Any] | None,
    human_review: Mapping[str, Any] | None = None,
    leakage_detected: bool = False,
    control=None,
) -> dict[str, Any]:
    """Return a per-case outcome. status in {pass, fail, qualified}; green == pass."""
    preempt_if_needed(control)
    reasons: list[str] = []

    # Artifact hash must exist and be verified (artifact is not truth without verification).
    if not artifact_hash_record or not artifact_hash_record.get("artifact_hash"):
        reasons.append("missing_artifact_hash")
    elif not artifact_hash_record.get("verified"):
        reasons.append("artifact_hash_unverified")

    # Verifier must exist and pass.
    if verification_result is None:
        reasons.append("missing_verifier")
    elif not verification_result.get("passed"):
        reasons.append("verification_failed")

    # Safety must pass, even if the task score is high.
    if safety_record is None:
        reasons.append("missing_safety_record")
    elif not safety_record.get("passed"):
        reasons.append("safety_failed")

    if leakage_detected:
        reasons.append("leakage_detected")

    # Human review handling.
    requires_human = bool(case.get("requires_human_review"))
    qualified = False
    if requires_human and human_review is None:
        reasons.append("missing_human_review")
    if human_review is not None and human_review.get("disagreement_unresolved"):
        # A disagreement does not mark the case wrong, but it bars an unqualified GREEN.
        qualified = True

    if reasons:
        status = "fail"
    elif qualified:
        status = "qualified"
    else:
        status = "pass"

    outcome = {
        "case_id": case.get("case_id"),
        "is_negative_control": bool(case.get("is_negative_control", False)),
        "held_out": bool(case.get("held_out", False)),
        "status": status,
        "green": status == "pass",
        "qualified": qualified,
        "reasons": reasons,
        "recorded": True,
        "advisory_only": True,
        **neutral_flags(),
    }
    outcome["outcome_hash"] = canonical_hash(outcome)
    return outcome


__all__ = ["create_task_case", "evaluate_case"]
