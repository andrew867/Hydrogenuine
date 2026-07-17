"""Quality receipt factory for output quality review.

A quality receipt is NOT a truth certificate. promotion_allowed is always
False. grants_authority is always False. Model output is not truth.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from hg_runtime.output_quality.schemas import QUALITY_CLASSES

ACTIONS = {
    "accept",
    "accept_with_low_confidence",
    "retry_same_model",
    "route_to_synthesis_model",
    "route_to_units_model",
    "route_to_safety_auditor",
    "mark_low_value",
    "operator_review_required",
    "quarantine_candidate",
    "reject_for_boundary_violation",
}


def _compute_output_hash(content: str) -> str:
    """SHA-256 hash of the raw content bytes."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _receipt_id(receipt: dict) -> str:
    raw = json.dumps(receipt, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_quality_receipt(
    content: str,
    *,
    model_id: str,
    run_id: str = "",
    seed_id: str = "",
    task_id: str = "",
    mode: str = "",
    review_id: str = "",
) -> dict:
    """Create a quality review receipt for a piece of model output.

    The receipt is a data structure only. It does NOT grant authority,
    does NOT promote to knowledge, and does NOT treat model output as truth.
    """
    receipt = {
        "schema": "quality_receipt_v2",
        "quality_review_id": "",
        "run_id": run_id,
        "review_id": review_id,
        "seed_id": seed_id,
        "task_id": task_id,
        "mode": mode,
        "model": model_id,
        "output_hash": _compute_output_hash(content),
        "quality_score": 0.0,
        "detected_issues": [],
        "recommended_action": "accept",
        "actual_action": "accept",
        "escalation_model_if_any": "",
        "promotion_allowed": False,
        "operator_review_required": False,
        "boundary_flags": [],
        "final_quality_verdict": "",
        "grants_authority": False,
        "model_output_treated_as_truth": False,
        "created_at": _utc_now_iso(),
    }
    receipt["quality_review_id"] = _receipt_id(receipt)
    return receipt


def validate_quality_receipt(receipt: dict) -> list[str]:
    """Validate a quality receipt. Returns list of error strings (empty = valid)."""
    errors = []

    if receipt.get("schema") != "quality_receipt_v2":
        errors.append(f"wrong schema: {receipt.get('schema')}")

    if receipt.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")
    if receipt.get("grants_authority") is not False:
        errors.append("grants_authority must be False")
    if receipt.get("model_output_treated_as_truth") is not False:
        errors.append("model_output_treated_as_truth must be False")

    action = receipt.get("recommended_action")
    if action and action not in ACTIONS:
        errors.append(f"unknown recommended_action: {action}")

    actual = receipt.get("actual_action")
    if actual and actual not in ACTIONS:
        errors.append(f"unknown actual_action: {actual}")

    verdict = receipt.get("final_quality_verdict")
    if verdict and verdict not in QUALITY_CLASSES:
        errors.append(f"unknown final_quality_verdict: {verdict}")

    score = receipt.get("quality_score", 0.0)
    if not (0.0 <= score <= 1.0):
        errors.append(f"quality_score out of range: {score}")

    if not receipt.get("output_hash"):
        errors.append("missing output_hash")

    return errors
