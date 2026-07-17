"""Output quality adjudicator schemas and constants."""

from __future__ import annotations

SCHEMA_VERSION = "output_quality_receipt_v1"

QUALITY_CLASSES = {
    "HIGH_VALUE",
    "USABLE_WITH_CAVEATS",
    "LOW_VALUE_TRIAGE",
    "RETRY_WITH_DIFFERENT_MODEL",
    "ROUTE_TO_SYNTHESIS",
    "ROUTE_TO_OPERATOR_REVIEW",
    "REJECT_UNSUPPORTED",
    "REJECT_UNSAFE_OVERCLAIM",
}

ISSUE_CATEGORIES = {
    "repetitive",
    "circular",
    "generic_slop",
    "fake_falsification",
    "category_confusion",
    "unsupported_assertion",
    "unsafe_overclaim",
    "off_topic_synthesis",
    "prompt_noncompliance",
    "weak_units_analysis",
    "known_physics_vs_speculation_confusion",
    "metaphor_treated_as_mechanism",
    "source_discovery_treated_as_evidence",
    "low_value_small_model_output",
    "truncated_needs_retry",
}

REJECT_CLASSES = {"REJECT_UNSUPPORTED", "REJECT_UNSAFE_OVERCLAIM"}

PROMOTABLE_CLASSES = {"HIGH_VALUE", "USABLE_WITH_CAVEATS"}

UNSAFE_OVERCLAIM_TERMS = [
    "agi", "artificial general intelligence",
    "conscious", "consciousness", "sentient", "sentience",
    "alive", "autonomous life", "sovereign",
    "new physics discovered", "proved new physics",
    "self-directed external action",
]


def empty_receipt() -> dict:
    return {
        "schema": SCHEMA_VERSION,
        "receipt_id": "",
        "source_receipt_id": "",
        "run_id": "",
        "seed_id": "",
        "task_id": "",
        "model_id": "",
        "science_mode": "",
        "output_classification": "",
        "quality_class": "",
        "issue_categories": [],
        "slop_score": 0.0,
        "repetition_score": 0.0,
        "specificity_score": 0.0,
        "unsupported_claim_count": 0,
        "unsafe_overclaim_count": 0,
        "source_required": False,
        "recommended_route": "",
        "operator_review_required": False,
        "grants_authority": False,
        "promotes_to_knowledge": False,
        "model_output_treated_as_truth": False,
    }


def validate_receipt(receipt: dict) -> list[str]:
    errors = []
    if receipt.get("schema") != SCHEMA_VERSION:
        errors.append(f"wrong schema: {receipt.get('schema')}")
    if receipt.get("quality_class") and receipt["quality_class"] not in QUALITY_CLASSES:
        errors.append(f"unknown quality_class: {receipt['quality_class']}")
    for cat in receipt.get("issue_categories", []):
        if cat not in ISSUE_CATEGORIES:
            errors.append(f"unknown issue_category: {cat}")
    if receipt.get("grants_authority"):
        errors.append("grants_authority must be False")
    if receipt.get("promotes_to_knowledge"):
        errors.append("promotes_to_knowledge must be False")
    if receipt.get("model_output_treated_as_truth"):
        errors.append("model_output_treated_as_truth must be False")
    return errors
