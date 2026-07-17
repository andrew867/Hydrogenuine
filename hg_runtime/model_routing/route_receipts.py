"""Route receipts — records of routing decisions, contradictions, and agreements.

Model consensus is not proof. Model disagreement is contradiction, not truth decision.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

SCHEMA_VERSION = "persona_model_route_receipt_v1"

ROUTE_VERDICTS = frozenset({
    "APPROVED",
    "DENIED",
    "MODIFIED",
    "DEFERRED",
    "STOP_PANIC",
})


def _receipt_id(seed_id: str, task_id: str) -> str:
    raw = f"{seed_id}:{task_id}:{datetime.now(timezone.utc).isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def create_route_receipt(
    *,
    run_id: str = "",
    review_id: str = "",
    seed_id: str,
    task_id: str,
    requested_task_type: str,
    proposed_persona_lens: str,
    approved_persona_lens: str,
    proposed_model: str,
    approved_model: str,
    model_lane: str,
    route_reason: str,
    resource_preflight_result: dict | None = None,
    forbidden_model_check: bool = False,
    authority_field_scan: list[str] | None = None,
    final_route_verdict: str,
) -> dict:
    if final_route_verdict not in ROUTE_VERDICTS:
        raise ValueError(f"invalid route verdict: {final_route_verdict}")

    return {
        "schema": SCHEMA_VERSION,
        "route_id": _receipt_id(seed_id, task_id),
        "run_id": run_id,
        "review_id": review_id,
        "seed_id": seed_id,
        "task_id": task_id,
        "requested_task_type": requested_task_type,
        "proposed_persona_lens": proposed_persona_lens,
        "approved_persona_lens": approved_persona_lens,
        "proposed_model": proposed_model,
        "approved_model": approved_model,
        "model_lane": model_lane,
        "route_reason": route_reason,
        "resource_preflight_result": resource_preflight_result or {},
        "forbidden_model_check": forbidden_model_check,
        "authority_field_scan": authority_field_scan or [],
        "promotion_allowed": False,
        "operator_review_required": True,
        "final_route_verdict": final_route_verdict,
        "model_output_is_not_truth": True,
        "model_consensus_is_not_proof": True,
        "persona_is_not_identity": True,
        "persona_is_not_authority": True,
    }


def validate_route_receipt(receipt: dict) -> list[str]:
    violations = []
    if receipt.get("promotion_allowed"):
        violations.append("promotion_allowed_in_receipt")
    if not receipt.get("operator_review_required"):
        violations.append("operator_review_not_required")
    if not receipt.get("model_output_is_not_truth"):
        violations.append("model_output_treated_as_truth")
    if not receipt.get("model_consensus_is_not_proof"):
        violations.append("model_consensus_treated_as_proof")
    if not receipt.get("persona_is_not_identity"):
        violations.append("persona_treated_as_identity")
    if not receipt.get("persona_is_not_authority"):
        violations.append("persona_treated_as_authority")
    if receipt.get("final_route_verdict") not in ROUTE_VERDICTS:
        violations.append("invalid_route_verdict")
    return violations


def create_contradiction_receipt(
    *,
    seed_id: str,
    task_id: str,
    model_a: str,
    model_b: str,
    claim_a: str,
    claim_b: str,
    contradiction_type: str = "model_disagreement",
) -> dict:
    return {
        "schema": "contradiction_receipt_v1",
        "receipt_id": _receipt_id(seed_id, task_id),
        "seed_id": seed_id,
        "task_id": task_id,
        "model_a": model_a,
        "model_b": model_b,
        "claim_a": claim_a,
        "claim_b": claim_b,
        "contradiction_type": contradiction_type,
        "resolved_to_truth": False,
        "model_disagreement_is_truth_decision": False,
        "operator_review_required": True,
        "promotion_allowed": False,
    }


def create_agreement_receipt(
    *,
    seed_id: str,
    task_id: str,
    model_a: str,
    model_b: str,
    shared_claim: str,
    agreement_type: str = "model_consensus",
) -> dict:
    return {
        "schema": "agreement_receipt_v1",
        "receipt_id": _receipt_id(seed_id, task_id),
        "seed_id": seed_id,
        "task_id": task_id,
        "model_a": model_a,
        "model_b": model_b,
        "shared_claim": shared_claim,
        "agreement_type": agreement_type,
        "consensus_is_proof": False,
        "model_consensus_is_not_proof": True,
        "operator_review_required": True,
        "promotion_allowed": False,
    }


def validate_contradiction_receipt(receipt: dict) -> list[str]:
    violations = []
    if receipt.get("resolved_to_truth"):
        violations.append("contradiction_resolved_to_truth")
    if receipt.get("model_disagreement_is_truth_decision"):
        violations.append("disagreement_treated_as_truth_decision")
    if receipt.get("promotion_allowed"):
        violations.append("promotion_allowed")
    return violations


def validate_agreement_receipt(receipt: dict) -> list[str]:
    violations = []
    if receipt.get("consensus_is_proof"):
        violations.append("consensus_treated_as_proof")
    if not receipt.get("model_consensus_is_not_proof"):
        violations.append("consensus_proof_flag_missing")
    if receipt.get("promotion_allowed"):
        violations.append("promotion_allowed")
    return violations
