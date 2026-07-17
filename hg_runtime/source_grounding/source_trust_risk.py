"""Source trust/risk scoring — advisory only.

Trust score is not truth. Risk score is not disproof.
Score never grants promotion. Score never authorizes external action.
Score only affects review priority and wording.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

SOURCE_TYPES = {
    "primary_paper", "preprint", "official_documentation",
    "standards_reference", "science_news", "encyclopedia",
    "blog", "unknown",
}

DOMAIN_CATEGORIES = {
    "journal", "government", "academic", "standards",
    "news", "wiki", "unknown",
}

_DOMAIN_CATEGORY_MAP = {
    "nature.com": "journal",
    "science.org": "journal",
    "arxiv.org": "academic",
    "doi.org": "journal",
    "pubmed.ncbi.nlm.nih.gov": "journal",
    "nist.gov": "government",
    "cern.ch": "academic",
    "home.cern": "academic",
    "gov": "government",
    "edu": "academic",
    "wikipedia.org": "wiki",
    "en.wikipedia.org": "wiki",
}

_TYPE_TRUST_WEIGHT = {
    "primary_paper": 8,
    "preprint": 6,
    "official_documentation": 7,
    "standards_reference": 9,
    "science_news": 4,
    "encyclopedia": 5,
    "blog": 2,
    "unknown": 1,
}

_CATEGORY_TRUST_WEIGHT = {
    "journal": 8,
    "government": 7,
    "academic": 7,
    "standards": 9,
    "news": 4,
    "wiki": 5,
    "unknown": 2,
}


def classify_domain(domain: str) -> str:
    """Classify a domain into a category."""
    domain_lower = domain.lower()
    for pattern, category in _DOMAIN_CATEGORY_MAP.items():
        if pattern in domain_lower:
            return category
    if domain_lower.endswith(".gov"):
        return "government"
    if domain_lower.endswith(".edu"):
        return "academic"
    return "unknown"


def score_source(
    *,
    source_candidate_id: str = "",
    source_receipt_id: str = "",
    source_type: str = "unknown",
    domain: str = "",
    access_status: str = "public",
    fetched: bool = False,
    screenshot_captured: bool = False,
    text_extracted: bool = False,
    direct_claims_count: int = 0,
    inferred_claims_count: int = 0,
    unsupported_leap_count: int = 0,
    speculative_bridge_count: int = 0,
    unsafe_overclaim_count: int = 0,
    operator_priority: int | None = None,
) -> dict:
    """Score a source for review priority.

    Returns advisory scores only. Trust score is not truth.
    Risk score is not disproof.
    """
    domain_category = classify_domain(domain)

    type_weight = _TYPE_TRUST_WEIGHT.get(source_type, 1)
    category_weight = _CATEGORY_TRUST_WEIGHT.get(domain_category, 2)

    trust_base = (type_weight + category_weight) / 2.0

    if access_status == "public" and fetched:
        trust_base += 1.0
    if text_extracted:
        trust_base += 0.5
    if screenshot_captured:
        trust_base += 0.5

    trust_score = min(10.0, max(0.0, trust_base))

    risk_base = 0.0
    risk_reasons = []
    if unsupported_leap_count > 0:
        risk_base += unsupported_leap_count * 2.0
        risk_reasons.append(f"{unsupported_leap_count} unsupported leaps")
    if speculative_bridge_count > 0:
        risk_base += speculative_bridge_count * 1.5
        risk_reasons.append(f"{speculative_bridge_count} speculative bridges")
    if unsafe_overclaim_count > 0:
        risk_base += unsafe_overclaim_count * 3.0
        risk_reasons.append(f"{unsafe_overclaim_count} unsafe overclaims")
    if access_status in ("paywalled_preview", "blocked", "failed"):
        risk_base += 2.0
        risk_reasons.append(f"access: {access_status}")
    if not fetched:
        risk_base += 1.0
        risk_reasons.append("not fetched")

    risk_score = min(10.0, max(0.0, risk_base))

    if operator_priority is not None:
        review_priority = operator_priority
    else:
        review_priority = max(1, min(10, int(risk_score * 0.6 + (10 - trust_score) * 0.4)))

    scoring_reasons = []
    scoring_reasons.append(f"type={source_type} (weight {type_weight})")
    scoring_reasons.append(f"domain={domain_category} (weight {category_weight})")
    if risk_reasons:
        scoring_reasons.extend(risk_reasons)

    return {
        "source_candidate_id": source_candidate_id,
        "source_receipt_id": source_receipt_id,
        "trust_score": round(trust_score, 1),
        "risk_score": round(risk_score, 1),
        "review_priority": review_priority,
        "source_type": source_type,
        "domain_category": domain_category,
        "scoring_reasons": scoring_reasons,
        "trust_score_is_truth": False,
        "risk_score_is_disproof": False,
        "promotion_allowed": False,
        "operator_review_required": True,
    }
