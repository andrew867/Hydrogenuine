"""Adjudicator v2 — multi-model comparison, contradiction detection,
confidence banding, persona lens enrichment, batch adjudication.

Model output is not truth. Model consensus is not proof.
Contradiction is not a truth decision — it is a signal for operator review.
"""

from __future__ import annotations

import hashlib
import json

from hg_runtime.output_quality.schemas import (
    QUALITY_CLASSES,
    REJECT_CLASSES,
    PROMOTABLE_CLASSES,
    ISSUE_CATEGORIES,
    UNSAFE_OVERCLAIM_TERMS,
    empty_receipt,
    validate_receipt,
)
from hg_runtime.output_quality.classifier import classify
from hg_runtime.output_quality.adjudicator import (
    adjudicate as adjudicate_v1,
    may_promote,
    is_rejected,
)
from hg_runtime.model_routing.persona_model_router import TASK_PERSONA_MAP, TASK_TYPES

SCHEMA_VERSION_V2 = "output_quality_receipt_v2"

CONFIDENCE_BANDS = {"high", "medium", "low"}


def _hash_receipt(record: dict) -> str:
    raw = json.dumps(record, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _persona_lens_for_task(task_type: str) -> str:
    """Look up persona_lens from TASK_PERSONA_MAP. Returns '' if not found."""
    entry = TASK_PERSONA_MAP.get(task_type)
    if entry:
        return entry[0]
    return ""


def _confidence_band(scores: list[float]) -> str:
    """Classify confidence based on score spread across outputs.

    For a single output, use the quality scores to determine band.
    For multiple outputs, use the spread between them.
    """
    if not scores:
        return "low"
    if len(scores) == 1:
        val = scores[0]
        if val >= 0.7:
            return "high"
        elif val >= 0.4:
            return "medium"
        return "low"
    spread = max(scores) - min(scores)
    if spread < 0.15:
        return "high"
    elif spread < 0.4:
        return "medium"
    return "low"


def _enforce_invariants(receipt: dict) -> dict:
    """Ensure all safety invariants are set."""
    receipt["model_output_treated_as_truth"] = False
    receipt["grants_authority"] = False
    receipt["promotes_to_knowledge"] = False
    receipt["model_consensus_is_not_proof"] = True
    receipt["promotion_allowed"] = False
    return receipt


# ── Single-output adjudication (v2-enriched) ──


def adjudicate_v2(
    content: str,
    *,
    model_id: str,
    run_id: str = "",
    seed_id: str = "",
    task_id: str = "",
    task_type: str = "",
    science_mode: str = "",
    source_receipt_id: str = "",
    char_count: int = 0,
    classification: str = "",
    stop_panic: bool = False,
) -> dict:
    """Enhanced single-output adjudication with persona_lens and confidence_band."""

    if stop_panic:
        receipt = empty_receipt()
        receipt.update({
            "schema": SCHEMA_VERSION_V2,
            "run_id": run_id,
            "seed_id": seed_id,
            "task_id": task_id,
            "model_id": model_id,
            "quality_class": "",
            "recommended_route": "STOP_PANIC",
            "operator_review_required": True,
            "persona_lens": "",
            "confidence_band": "low",
        })
        receipt = _enforce_invariants(receipt)
        receipt["receipt_id"] = _hash_receipt(receipt)
        return receipt

    if char_count == 0:
        char_count = len(content)

    result = classify(
        content, model_id, char_count,
        classification=classification, science_mode=science_mode,
    )

    persona_lens = _persona_lens_for_task(task_type)

    # Confidence band from specificity score (single output)
    confidence_band = _confidence_band([result["specificity_score"]])

    receipt = empty_receipt()
    receipt.update({
        "schema": SCHEMA_VERSION_V2,
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
        "persona_lens": persona_lens,
        "confidence_band": confidence_band,
    })
    receipt = _enforce_invariants(receipt)

    # If there is any unsafe content or contradiction, operator must review
    if result["unsafe_overclaim_count"] > 0:
        receipt["operator_review_required"] = True

    receipt["receipt_id"] = _hash_receipt(receipt)
    return receipt


# ── Multi-model comparison ──


def compare_model_outputs(
    outputs: list[dict],
    *,
    seed_id: str,
    task_id: str,
    task_type: str = "",
    stop_panic: bool = False,
) -> dict:
    """Compare outputs from multiple models on the same seed/task.

    Each item in outputs: {"model_id": str, "content": str}

    Returns a comparison receipt with agreement/contradiction entries.
    Model consensus is NOT proof. Model disagreement is NOT a truth decision.
    """
    if stop_panic:
        return _enforce_invariants({
            "schema": SCHEMA_VERSION_V2,
            "receipt_type": "comparison",
            "seed_id": seed_id,
            "task_id": task_id,
            "entries": [],
            "agreement_count": 0,
            "contradiction_count": 0,
            "confidence_band": "low",
            "operator_review_required": True,
            "blocked": True,
            "receipt_id": "",
            "model_output_treated_as_truth": False,
            "grants_authority": False,
            "promotes_to_knowledge": False,
            "model_consensus_is_not_proof": True,
            "promotion_allowed": False,
        })

    # Adjudicate each output individually
    individual_receipts = []
    for item in outputs:
        r = adjudicate_v2(
            item["content"],
            model_id=item["model_id"],
            seed_id=seed_id,
            task_id=task_id,
            task_type=task_type,
        )
        individual_receipts.append(r)

    # Compare quality classes pairwise
    entries = []
    for i in range(len(individual_receipts)):
        for j in range(i + 1, len(individual_receipts)):
            ra = individual_receipts[i]
            rb = individual_receipts[j]

            model_a = outputs[i]["model_id"]
            model_b = outputs[j]["model_id"]

            classes_agree = ra["quality_class"] == rb["quality_class"]
            issues_a = set(ra.get("issue_categories", []))
            issues_b = set(rb.get("issue_categories", []))
            issues_agree = issues_a == issues_b

            if classes_agree and issues_agree:
                entries.append({
                    "type": "agreement",
                    "model_a": model_a,
                    "model_b": model_b,
                    "shared_quality_class": ra["quality_class"],
                    "note": "Models agree on quality class and issue categories.",
                })
            else:
                entries.append({
                    "type": "contradiction",
                    "model_a": model_a,
                    "model_b": model_b,
                    "quality_class_a": ra["quality_class"],
                    "quality_class_b": rb["quality_class"],
                    "issues_a": sorted(issues_a),
                    "issues_b": sorted(issues_b),
                    "note": "Models disagree. This is NOT a truth decision.",
                    "resolved_to_truth": False,
                })

    agreement_count = sum(1 for e in entries if e["type"] == "agreement")
    contradiction_count = sum(1 for e in entries if e["type"] == "contradiction")

    # Confidence band from specificity scores
    spec_scores = [r["specificity_score"] for r in individual_receipts]
    confidence_band = _confidence_band(spec_scores)

    comparison = {
        "schema": SCHEMA_VERSION_V2,
        "receipt_type": "comparison",
        "seed_id": seed_id,
        "task_id": task_id,
        "entries": entries,
        "agreement_count": agreement_count,
        "contradiction_count": contradiction_count,
        "confidence_band": confidence_band,
        "operator_review_required": contradiction_count > 0,
        "blocked": False,
    }
    comparison = _enforce_invariants(comparison)
    comparison["receipt_id"] = _hash_receipt(comparison)
    return comparison


# ── Batch adjudication ──


def batch_adjudicate(
    items: list[dict],
    *,
    run_id: str,
    stop_panic: bool = False,
) -> dict:
    """Adjudicate a batch of outputs and return summary statistics.

    Each item: {"model_id": str, "content": str, "seed_id": str, "task_id": str}
    Optional per-item: "task_type": str
    """
    if stop_panic:
        return _enforce_invariants({
            "schema": SCHEMA_VERSION_V2,
            "receipt_type": "batch_summary",
            "run_id": run_id,
            "total": 0,
            "receipts": [],
            "high_value_count": 0,
            "reject_count": 0,
            "operator_review_count": 0,
            "blocked": True,
            "receipt_id": "",
            "model_output_treated_as_truth": False,
            "grants_authority": False,
            "promotes_to_knowledge": False,
            "model_consensus_is_not_proof": True,
            "promotion_allowed": False,
        })

    receipts = []
    for item in items:
        r = adjudicate_v2(
            item["content"],
            model_id=item["model_id"],
            run_id=run_id,
            seed_id=item.get("seed_id", ""),
            task_id=item.get("task_id", ""),
            task_type=item.get("task_type", ""),
        )
        receipts.append(r)

    high_value_count = sum(
        1 for r in receipts if r.get("quality_class") in PROMOTABLE_CLASSES
    )
    reject_count = sum(
        1 for r in receipts if r.get("quality_class") in REJECT_CLASSES
    )
    operator_review_count = sum(
        1 for r in receipts if r.get("operator_review_required")
    )

    summary = {
        "schema": SCHEMA_VERSION_V2,
        "receipt_type": "batch_summary",
        "run_id": run_id,
        "total": len(receipts),
        "receipts": receipts,
        "high_value_count": high_value_count,
        "reject_count": reject_count,
        "operator_review_count": operator_review_count,
        "operator_review_required": operator_review_count > 0 or reject_count > 0,
        "blocked": False,
    }
    summary = _enforce_invariants(summary)
    summary["receipt_id"] = _hash_receipt(summary)
    return summary


# ── Receipt validation ──


def validate_v2_receipt(receipt: dict) -> list[str]:
    """Validate a v2 receipt. Returns list of error strings (empty = valid)."""
    errors = []

    schema = receipt.get("schema")
    if schema != SCHEMA_VERSION_V2:
        errors.append(f"wrong schema: expected {SCHEMA_VERSION_V2}, got {schema}")

    # Invariant checks — these must always hold
    if receipt.get("model_output_treated_as_truth") is not False:
        errors.append("model_output_treated_as_truth must be False")
    if receipt.get("grants_authority") is not False:
        errors.append("grants_authority must be False")
    if receipt.get("promotes_to_knowledge") is not False:
        errors.append("promotes_to_knowledge must be False")
    if receipt.get("model_consensus_is_not_proof") is not True:
        errors.append("model_consensus_is_not_proof must be True")
    if receipt.get("promotion_allowed") is not False:
        errors.append("promotion_allowed must be False")

    # Quality class check for single receipts
    qc = receipt.get("quality_class")
    if qc is not None and qc != "" and qc not in QUALITY_CLASSES:
        errors.append(f"unknown quality_class: {qc}")

    # Confidence band check
    cb = receipt.get("confidence_band")
    if cb is not None and cb not in CONFIDENCE_BANDS:
        errors.append(f"unknown confidence_band: {cb}")

    # Issue categories check
    for cat in receipt.get("issue_categories", []):
        if cat not in ISSUE_CATEGORIES:
            errors.append(f"unknown issue_category: {cat}")

    # Operator review required for contradictions or unsafe content
    if receipt.get("receipt_type") == "comparison":
        if receipt.get("contradiction_count", 0) > 0 and not receipt.get("operator_review_required"):
            errors.append("operator_review_required must be True when contradictions exist")

    # Batch-level: reject_count > 0 must flag operator review
    if receipt.get("receipt_type") == "batch_summary":
        if receipt.get("reject_count", 0) > 0 and not receipt.get("operator_review_required"):
            errors.append("operator_review_required must be True when batch contains rejected outputs")

    return errors
