"""Adjudicator — orchestrate scoring, rules, classifier into a decision."""

from __future__ import annotations

import hashlib
import json

from hg_runtime.output_quality.schemas import empty_receipt, REJECT_CLASSES, PROMOTABLE_CLASSES
from hg_runtime.output_quality.classifier import classify


def adjudicate(content: str, *, model_id: str, run_id: str = "",
               seed_id: str = "", task_id: str = "", science_mode: str = "",
               source_receipt_id: str = "", char_count: int = 0,
               classification: str = "") -> dict:
    """Produce a quality receipt for a model output."""

    if char_count == 0:
        char_count = len(content)

    result = classify(content, model_id, char_count,
                      classification=classification, science_mode=science_mode)

    receipt = empty_receipt()
    receipt.update({
        "source_receipt_id": source_receipt_id,
        "run_id": run_id,
        "seed_id": seed_id,
        "task_id": task_id,
        "model_id": model_id,
        "science_mode": science_mode,
        "output_classification": classification,
        "quality_class": result["quality_class"],
        "issue_categories": result["issue_categories"],
        "slop_score": result["slop_score"],
        "repetition_score": result["repetition_score"],
        "specificity_score": result["specificity_score"],
        "unsupported_claim_count": result["unsupported_claim_count"],
        "unsafe_overclaim_count": result["unsafe_overclaim_count"],
        "source_required": result["source_required"],
        "recommended_route": result["recommended_route"],
        "operator_review_required": result["operator_review_required"],
        "grants_authority": False,
        "promotes_to_knowledge": False,
        "model_output_treated_as_truth": False,
    })

    raw = json.dumps(receipt, sort_keys=True)
    receipt["receipt_id"] = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return receipt


def may_promote(receipt: dict) -> bool:
    """Whether this output may be promoted to memory/knowledge."""
    return (receipt.get("quality_class") in PROMOTABLE_CLASSES
            and receipt.get("unsafe_overclaim_count", 0) == 0
            and not receipt.get("operator_review_required")
            and receipt.get("quality_class") not in REJECT_CLASSES)


def is_rejected(receipt: dict) -> bool:
    return receipt.get("quality_class") in REJECT_CLASSES
