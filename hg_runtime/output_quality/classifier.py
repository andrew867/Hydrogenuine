"""Feature extraction and quality classification."""

from __future__ import annotations

from hg_runtime.output_quality import scoring, rules
from hg_runtime.output_quality.schemas import (
    QUALITY_CLASSES, REJECT_CLASSES, PROMOTABLE_CLASSES,
)


def classify(content: str, model_id: str, char_count: int,
             classification: str = "", science_mode: str = "") -> dict:
    """Classify output quality. Returns quality_class, issue_categories, scores, route."""

    issues: list[str] = []
    quality_class = "HIGH_VALUE"
    route = "ROUTE_TO_SYNTHESIS"
    operator_review = False

    slop = scoring.slop_score(content)
    rep = scoring.repetition_score(content)
    spec = scoring.specificity_score(content)

    if classification == "truncated_content":
        issues.append("truncated_needs_retry")
        quality_class = "RETRY_WITH_DIFFERENT_MODEL"
        route = "RETRY_WITH_DIFFERENT_MODEL"

    if rules.detect_repetitive(content):
        issues.append("repetitive")
    if rules.detect_circular(content):
        issues.append("circular")
    if rules.detect_generic_slop(content):
        issues.append("generic_slop")
    if rules.detect_fake_falsification(content):
        issues.append("fake_falsification")

    overclaims = rules.detect_unsafe_overclaim(content)
    if overclaims:
        issues.append("unsafe_overclaim")
        quality_class = "REJECT_UNSAFE_OVERCLAIM"
        route = "ROUTE_TO_OPERATOR_REVIEW"
        operator_review = True

    if rules.detect_category_confusion(content):
        issues.append("category_confusion")
    if rules.detect_metaphor_as_mechanism(content):
        issues.append("metaphor_treated_as_mechanism")
    if rules.detect_source_discovery_as_evidence(content):
        issues.append("source_discovery_treated_as_evidence")
    if rules.detect_unsupported_assertion(content):
        issues.append("unsupported_assertion")
    if rules.detect_low_value_small_model(content, model_id, char_count):
        issues.append("low_value_small_model_output")

    if quality_class not in REJECT_CLASSES and quality_class != "RETRY_WITH_DIFFERENT_MODEL":
        if "fake_falsification" in issues:
            quality_class = "REJECT_UNSUPPORTED"
            route = "ROUTE_TO_OPERATOR_REVIEW"
            operator_review = True
        elif len(issues) >= 3 or (slop > 0.5 and rep > 0.3):
            quality_class = "LOW_VALUE_TRIAGE"
            route = "RETRY_WITH_DIFFERENT_MODEL"
        elif "low_value_small_model_output" in issues:
            quality_class = "LOW_VALUE_TRIAGE"
            route = "RETRY_WITH_DIFFERENT_MODEL"
        elif len(issues) >= 1 and quality_class not in {"RETRY_WITH_DIFFERENT_MODEL"}:
            quality_class = "USABLE_WITH_CAVEATS"
            if any(i in issues for i in ["category_confusion", "metaphor_treated_as_mechanism"]):
                route = "ROUTE_TO_OPERATOR_REVIEW"
                operator_review = True

    source_required = "source_discovery_treated_as_evidence" in issues

    return {
        "quality_class": quality_class,
        "issue_categories": issues,
        "slop_score": round(slop, 3),
        "repetition_score": round(rep, 3),
        "specificity_score": round(spec, 3),
        "unsupported_claim_count": 1 if "unsupported_assertion" in issues else 0,
        "unsafe_overclaim_count": len(overclaims),
        "source_required": source_required,
        "recommended_route": route,
        "operator_review_required": operator_review,
    }
